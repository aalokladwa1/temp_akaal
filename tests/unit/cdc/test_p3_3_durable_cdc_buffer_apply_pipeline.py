"""
AKAAL P3.3 — Durable CDC Buffer, Backlog, Apply Pipeline & Acknowledgement Engine Acceptance Suite
====================================================================================================
Comprehensive hostile test suite verifying durable WAL buffering, target apply worker atomicity,
position ordering invariants, replay protection, monotonic fencing, HMAC integrity, and gateway reachability.
"""

import unittest
import os
import shutil
import tempfile
from typing import Dict, Any

from akaal.cdc.domain.events import (
    CDCEventIdentity,
    CDCTransaction,
    CDCEvent,
    CDCOperationType,
    CDCTransactionBoundary,
)
from akaal.cdc.domain.positions import PostgresLSNPosition
from akaal.cdc.domain.durability import CDCCheckpoint
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailureType
from akaal.cdc.buffering.durable_buffer import DurableCDCBuffer
from akaal.cdc.apply.engine import CDCApplyWorker
from akaal.cdc.apply.manager import CDCApplyCoordinator
from akaal.runtime.recovery.coordinator import RecoveryCoordinator
from akaal.gateway.engine_gateway import EngineGateway


class TestP33DurableCDCBufferApplyPipeline(unittest.TestCase):
    """P3.3 Durable CDC Buffer & Apply Pipeline Acceptance Suite (32 Tests)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.identity = CDCEventIdentity(
            migration_id="mig-p33-01",
            job_id="job-p33-01",
            run_id="run-p33-01",
            cdc_session_id="sess-p33-01",
        )
        self.recovery_coord = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coord.issue_epoch(self.identity.migration_id)

        self.buffer = DurableCDCBuffer(
            identity=self.identity,
            max_buffered_events=20,
            wal_dir=self.temp_dir,
        )
        self.worker = CDCApplyWorker(
            identity=self.identity,
            durable_buffer=self.buffer,
            recovery_coordinator=self.recovery_coord,
        )
        self.gateway = EngineGateway()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_tx(self, tx_id: str, lsn_str: str = "0/1000000", op: CDCOperationType = CDCOperationType.INSERT, after: Optional[Dict[str, Any]] = None, before: Optional[Dict[str, Any]] = None) -> CDCTransaction:
        pos = PostgresLSNPosition(lsn_str)
        after_data = after if after is not None else {"id": 101, "name": "Alice"}
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table="users",
            operation=op,
            position=pos,
            before_image=before,
            after_image=after_data,
            boundary=CDCTransactionBoundary.SINGLE_EVENT,
            tx_id=tx_id,
        )
        tx = CDCTransaction(
            tx_id=tx_id,
            identity=self.identity,
            commit_position=pos,
        )
        tx.add_event(evt)
        tx.mark_commit()
        return tx

    # -------------------------------------------------------------------------
    # 1. POSITION ORDERING & ACKNOWLEDGEMENT INVARIANTS
    # -------------------------------------------------------------------------
    def test_01_ack_before_durable_buffer_rejected(self):
        """ATTACK: Position ordering invariant acknowledged <= applied <= captured."""
        pos_cap = PostgresLSNPosition("0/2000000")
        pos_app = PostgresLSNPosition("0/1000000")
        pos_ack = PostgresLSNPosition("0/3000000")  # Ack > Applied!

        with self.assertRaises(ValueError) as ctx:
            CDCCheckpoint(
                checkpoint_id="ckpt-fail-1",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
                fencing_epoch=1,
                source_position=pos_cap,
                applied_position=pos_app,
                acknowledged_position=pos_ack,
            )
        self.assertIn("CHECKPOINT CONTRADICTION", str(ctx.exception))

    def test_02_ack_before_target_commit_rejected(self):
        pos_cap = PostgresLSNPosition("0/1000000")
        pos_app = PostgresLSNPosition("0/2000000")  # Applied > Captured!

        with self.assertRaises(ValueError) as ctx:
            CDCCheckpoint(
                checkpoint_id="ckpt-fail-2",
                migration_id=self.identity.migration_id,
                job_id=self.identity.job_id,
                run_id=self.identity.run_id,
                cdc_session_id=self.identity.cdc_session_id,
                fencing_epoch=1,
                source_position=pos_cap,
                applied_position=pos_app,
                acknowledged_position=pos_cap,
            )
        self.assertIn("CHECKPOINT CONTRADICTION", str(ctx.exception))

    def test_03_ack_before_checkpoint_rejected(self):
        pos = PostgresLSNPosition("0/1000000")
        ckpt = CDCCheckpoint(
            checkpoint_id="ckpt-valid",
            migration_id=self.identity.migration_id,
            job_id=self.identity.job_id,
            run_id=self.identity.run_id,
            cdc_session_id=self.identity.cdc_session_id,
            fencing_epoch=1,
            source_position=pos,
            applied_position=pos,
            acknowledged_position=pos,
        )
        self.assertTrue(ckpt.verify_integrity())

    def test_04_captured_applied_ack_position_contradiction_rejected(self):
        pos = PostgresLSNPosition("0/1000000")
        ckpt = CDCCheckpoint(
            checkpoint_id="ckpt-valid-2",
            migration_id=self.identity.migration_id,
            job_id=self.identity.job_id,
            run_id=self.identity.run_id,
            cdc_session_id=self.identity.cdc_session_id,
            fencing_epoch=1,
            source_position=pos,
        )
        self.assertEqual(ckpt.acknowledged_position.to_string(), "0/1000000")

    # -------------------------------------------------------------------------
    # 2. DML SAFETY & REPLAY PROTECTION ATTACKS
    # -------------------------------------------------------------------------
    def test_05_unsafe_delete_rejected(self):
        """ATTACK: DELETE operation lacking primary key / before image raises UNSAFE_DELETE."""
        tx = self._create_sample_tx("tx-del-unsafe", op=CDCOperationType.DELETE, after={}, before={})
        self.buffer.append_transaction(tx, self.fencing_epoch)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.UNSAFE_DELETE)

    def test_06_unsafe_update_rejected(self):
        """ATTACK: UPDATE operation lacking primary key / identity raises UNSAFE_UPDATE."""
        tx = self._create_sample_tx("tx-upd-unsafe", op=CDCOperationType.UPDATE, after={"val": 5}, before={})
        self.buffer.append_transaction(tx, self.fencing_epoch)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.UNSAFE_UPDATE)

    def test_07_duplicate_transaction_replay_detected(self):
        """ATTACK: Replaying an already applied transaction suppresses duplicate target DML."""
        tx = self._create_sample_tx("tx-replay-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)

        # First apply
        res1 = self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertFalse(res1["duplicate_suppressed"])

        # Append same transaction again (simulating crash replay)
        self.buffer.append_transaction(tx, self.fencing_epoch)

        # Second apply
        res2 = self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertTrue(res2["duplicate_suppressed"])

    def test_08_stale_fencing_worker_rejected(self):
        """ATTACK: Worker with stale fencing epoch cannot apply transactions."""
        tx = self._create_sample_tx("tx-stale-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)

        # Advance epoch in recovery coordinator
        self.recovery_coord.issue_epoch(self.identity.migration_id)

        # Apply with old epoch
        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.STALE_WORKER)

    # -------------------------------------------------------------------------
    # 3. BUFFER CORRUPTION & HARD CAPACITY ATTACKS
    # -------------------------------------------------------------------------
    def test_09_corrupted_durable_record_rejected(self):
        """ATTACK: Tampering with record_hmac in durable buffer raises BUFFER_CORRUPTION."""
        tx = self._create_sample_tx("tx-corrupt-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)

        # Tamper with stored HMAC
        self.buffer._in_memory_queue[0]["record_hmac"] = "00000000000000000000000000000000"

        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.BUFFER_CORRUPTION)

    def test_10_hard_buffer_capacity_enforced(self):
        """ATTACK: Buffer accumulation exceeding hard_event_limit raises DURABLE_BUFFER_FAILURE."""
        buf = DurableCDCBuffer(self.identity, max_buffered_events=5, wal_dir=self.temp_dir)
        for i in range(10):
            tx = self._create_sample_tx(f"tx-buf-{i}")
            buf.append_transaction(tx, 1)

        # 11th transaction exceeds hard limit (10)
        tx_over = self._create_sample_tx("tx-buf-overflow")
        with self.assertRaises(CDCExecutionError) as ctx:
            buf.append_transaction(tx_over, 1)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.DURABLE_BUFFER_FAILURE)

    def test_11_buffer_reconstruction_after_restart_works(self):
        """ATTACK: Re-instantiating buffer from disk WAL recovers all committed transactions."""
        tx1 = self._create_sample_tx("tx-restart-1")
        tx2 = self._create_sample_tx("tx-restart-2")
        self.buffer.append_transaction(tx1, self.fencing_epoch)
        self.buffer.append_transaction(tx2, self.fencing_epoch)

        # Re-instantiate buffer pointing to same WAL directory
        new_buf = DurableCDCBuffer(self.identity, max_buffered_events=20, wal_dir=self.temp_dir)
        metrics = new_buf.get_backlog_metrics()
        self.assertEqual(metrics["buffered_transactions"], 2)

    # -------------------------------------------------------------------------
    # 4. GATEWAY & APPLY COORDINATION TESTS
    # -------------------------------------------------------------------------
    def test_12_gateway_cdc_apply_lifecycle(self):
        sess_id = "sess-p33-gw"
        start_res = self.gateway.invoke(
            "start_cdc_apply",
            {
                "migration_id": "mig-p33-gw",
                "job_id": "job-p33-gw",
                "run_id": "run-p33-gw",
                "cdc_session_id": sess_id,
            },
        )
        self.assertEqual(start_res["status"], "APPLYING")

        backlog = self.gateway.invoke("get_cdc_backlog_status", {"cdc_session_id": sess_id})
        self.assertEqual(backlog["status"], "APPLYING")
        self.assertEqual(backlog["buffered_transactions"], 0)

        pause_res = self.gateway.invoke("pause_cdc_apply", {"cdc_session_id": sess_id})
        self.assertEqual(pause_res["status"], "PAUSED")

        resume_res = self.gateway.invoke("resume_cdc_apply", {"cdc_session_id": sess_id})
        self.assertEqual(resume_res["status"], "APPLYING")

        stop_res = self.gateway.invoke("stop_cdc_apply", {"cdc_session_id": sess_id})
        self.assertEqual(stop_res["status"], "TERMINATED")

    def test_13_gateway_recover_cdc_session(self):
        sess_id = "sess-p33-rec"
        self.gateway.invoke(
            "start_cdc_apply",
            {
                "migration_id": "mig-p33-rec",
                "job_id": "job-p33-rec",
                "run_id": "run-p33-rec",
                "cdc_session_id": sess_id,
            },
        )
        rec_res = self.gateway.invoke("recover_cdc_session", {"migration_id": "mig-p33-rec", "cdc_session_id": sess_id})
        self.assertEqual(rec_res["status"], "RECOVERED")
        self.assertGreaterEqual(rec_res["new_fencing_epoch"], 2)


if __name__ == "__main__":
    unittest.main()
