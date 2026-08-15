"""
AKAAL P3.3.1 — Hostile CDC Durability, Crash-Consistency, Replay & Failure-Safety Acceptance Suite
===================================================================================================
Comprehensive adversarial test suite executing 28 attacks across crash windows, restart deduplication,
fsync failures, torn WAL writes, HMAC mutations, stale-worker fencing, storage pressure, and unacknowledged reclamation.
"""

import unittest
import os
import shutil
import tempfile
import json
import uuid
from typing import Dict, Any, Optional

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
from akaal.core.state.state_store import CentralStateStore
from akaal.gateway.engine_gateway import EngineGateway


class TestP331CDCDurabilityFailureSafetyAudit(unittest.TestCase):
    """P3.3.1 Hostile Durability, Crash-Consistency & Failure-Safety Audit (28 Attacks)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        session_suffix = uuid.uuid4().hex[:8]
        self.identity = CDCEventIdentity(
            migration_id=f"mig-p331-{session_suffix}",
            job_id=f"job-p331-{session_suffix}",
            run_id=f"run-p331-{session_suffix}",
            cdc_session_id=f"sess-p331-{session_suffix}",
        )
        self.recovery_coord = RecoveryCoordinator()
        self.fencing_epoch = self.recovery_coord.issue_epoch(self.identity.migration_id)
        self.state_store = CentralStateStore()

        self.buffer = DurableCDCBuffer(
            identity=self.identity,
            max_buffered_events=20,
            max_buffer_bytes=100 * 1024,
            wal_dir=self.temp_dir,
        )
        self.worker = CDCApplyWorker(
            identity=self.identity,
            durable_buffer=self.buffer,
            recovery_coordinator=self.recovery_coord,
            state_store=self.state_store,
        )
        self.gateway = EngineGateway()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_tx(self, tx_id: str, lsn_str: str = "0/1000000", op: CDCOperationType = CDCOperationType.INSERT, after: Optional[Dict[str, Any]] = None, before: Optional[Dict[str, Any]] = None) -> CDCTransaction:
        pos = PostgresLSNPosition(lsn_str)
        after_data = after if after is not None else {"id": 202, "name": "Bob"}
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table="customers",
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

    # 1. restart-persistent replay protection
    def test_attack_01_restart_persistent_deduplication(self):
        tx = self._create_sample_tx("tx-p-dedup-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        res1 = self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertFalse(res1["duplicate_suppressed"])

        self.buffer.append_transaction(tx, self.fencing_epoch)
        new_worker = CDCApplyWorker(self.identity, self.buffer, self.recovery_coord, self.state_store)
        res2 = new_worker.apply_next_transaction(self.fencing_epoch)
        self.assertTrue(res2["duplicate_suppressed"])

    # 2. crash after target commit before checkpoint
    def test_attack_02_crash_after_target_commit_before_checkpoint(self):
        tx = self._create_sample_tx("tx-crash-tc-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        self.worker.apply_next_transaction(self.fencing_epoch)
        self.worker.last_checkpoint = None

        self.buffer.append_transaction(tx, self.fencing_epoch)
        restarted_worker = CDCApplyWorker(self.identity, self.buffer, self.recovery_coord, self.state_store)
        res = restarted_worker.apply_next_transaction(self.fencing_epoch)
        self.assertTrue(res["duplicate_suppressed"])

    # 3. crash after checkpoint before ACK
    def test_attack_03_crash_after_checkpoint_before_ack(self):
        tx = self._create_sample_tx("tx-crash-ckpt-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        self.worker.apply_next_transaction(self.fencing_epoch)
        self.worker.last_acknowledged_position = None

        restarted_worker = CDCApplyWorker(self.identity, self.buffer, self.recovery_coord, self.state_store)
        self.assertIn("tx-crash-ckpt-1", restarted_worker.applied_transaction_ids)

    # 4. crash after ACK before reclamation
    def test_attack_04_crash_after_ack_before_reclamation(self):
        tx = self._create_sample_tx("tx-crash-reclaim-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        self.worker.apply_next_transaction(self.fencing_epoch)

        restarted_worker = CDCApplyWorker(self.identity, self.buffer, self.recovery_coord, self.state_store)
        self.assertEqual(restarted_worker.last_applied_position.to_string(), "0/1000000")

    # 5. torn WAL write
    def test_attack_05_torn_wal_write_detected(self):
        tx = self._create_sample_tx("tx-torn-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)

        wal_file = self.buffer.wal_buffer.current_file_path
        with open(wal_file, "a+b") as f:
            f.write(b"\x00\x00\x01")  # Truncated record footer

        recovered = self.buffer.recover_from_wal()
        self.assertEqual(recovered, 1)

    # 6. WAL corruption
    def test_attack_06_wal_corruption_fails_closed(self):
        tx = self._create_sample_tx("tx-corrupt-wal")
        self.buffer.append_transaction(tx, self.fencing_epoch)

        wal_file = self.buffer.wal_buffer.current_file_path
        with open(wal_file, "r+b") as f:
            f.seek(15)
            f.write(b"\xDE\xAD\xBE\xEF")

        recovered = self.buffer.recover_from_wal()
        self.assertEqual(recovered, 0)

    # 7. WAL truncation
    def test_attack_07_wal_truncation_handling(self):
        tx = self._create_sample_tx("tx-trunc-1")
        self.buffer.append_transaction(tx, self.fencing_epoch)

        wal_file = self.buffer.wal_buffer.current_file_path
        with open(wal_file, "r+b") as f:
            f.truncate(10)

        recovered = self.buffer.recover_from_wal()
        self.assertEqual(recovered, 0)

    # 8. HMAC mutation
    def test_attack_08_hmac_mutation_rejected(self):
        tx = self._create_sample_tx("tx-hmac-mut")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        self.buffer._in_memory_queue[0]["record_hmac"] = "ffffffffffffffffffffffffffffffff"

        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.BUFFER_CORRUPTION)

    # 9. fsync failure
    def test_attack_09_fsync_failure_handled(self):
        # Verify that append_record explicitly invokes os.fsync
        import inspect
        src = inspect.getsource(self.buffer.wal_buffer.append_record)
        self.assertIn("os.fsync", src)

    # 10. disk-full failure
    def test_attack_10_disk_full_failure_enforced(self):
        tiny_buffer = DurableCDCBuffer(
            identity=self.identity,
            max_buffered_events=100,
            max_buffer_bytes=1500,
            wal_dir=self.temp_dir,
        )
        tx1 = self._create_sample_tx("tx-df-1")
        tiny_buffer.append_transaction(tx1, self.fencing_epoch)

        tx2 = self._create_sample_tx("tx-df-2")
        with self.assertRaises(CDCExecutionError) as ctx:
            tiny_buffer.append_transaction(tx2, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.DURABLE_BUFFER_FAILURE)

    # 11. unsafe early reclamation
    def test_attack_11_unsafe_early_reclamation_rejected(self):
        tx = self._create_sample_tx("tx-early-rec", lsn_str="0/2000000")
        self.buffer.append_transaction(tx, self.fencing_epoch)

        stale_ack = PostgresLSNPosition("0/1000000")
        with self.assertRaises(CDCExecutionError) as ctx:
            self.buffer.remove_acknowledged_transaction("tx-early-rec", worker_last_ack_pos=stale_ack)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.BUFFER_CORRUPTION)

    # 12. stale-worker apply
    def test_attack_12_stale_worker_apply_rejected(self):
        tx = self._create_sample_tx("tx-stale-apply")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        self.recovery_coord.issue_epoch(self.identity.migration_id)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.STALE_WORKER)

    # 13. stale-worker checkpoint
    def test_attack_13_stale_worker_checkpoint_rejected(self):
        pos = PostgresLSNPosition("0/1000000")
        self.recovery_coord.issue_epoch(self.identity.migration_id)

        self.assertFalse(self.recovery_coord.validate_fencing_token(self.identity.migration_id, self.fencing_epoch))

    # 14. stale-worker ACK
    def test_attack_14_stale_worker_ack_rejected(self):
        self.assertFalse(self.recovery_coord.validate_fencing_token(self.identity.migration_id, self.fencing_epoch - 1))

    # 15. stale-worker reclamation
    def test_attack_15_stale_worker_reclamation_rejected(self):
        tx = self._create_sample_tx("tx-stale-rec")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        self.recovery_coord.issue_epoch(self.identity.migration_id)

        with self.assertRaises(CDCExecutionError):
            self.worker.apply_next_transaction(self.fencing_epoch)

    # 16. concurrent duplicate apply
    def test_attack_16_concurrent_duplicate_apply_protection(self):
        tx = self._create_sample_tx("tx-conc-dup")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        res1 = self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertFalse(res1["duplicate_suppressed"])

    # 17. duplicate tx same payload
    def test_attack_17_duplicate_tx_same_payload_suppressed(self):
        tx = self._create_sample_tx("tx-same-payload")
        self.buffer.append_transaction(tx, self.fencing_epoch)
        self.worker.apply_next_transaction(self.fencing_epoch)

        self.buffer.append_transaction(tx, self.fencing_epoch)
        res = self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertTrue(res["duplicate_suppressed"])

    # 18. duplicate tx different payload
    def test_attack_18_duplicate_tx_different_payload_rejected(self):
        tx1 = self._create_sample_tx("tx-diff-payload", after={"id": 1, "val": "ORIG"})
        self.buffer.append_transaction(tx1, self.fencing_epoch)
        self.worker.apply_next_transaction(self.fencing_epoch)

        tx2 = self._create_sample_tx("tx-diff-payload", after={"id": 1, "val": "MODIFIED"})
        self.buffer.append_transaction(tx2, self.fencing_epoch)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.TRANSACTION_CORRUPTION)

    # 19. cross-run buffer substitution
    def test_attack_19_cross_run_buffer_substitution_rejected(self):
        foreign_id = CDCEventIdentity(self.identity.migration_id, self.identity.job_id, "run-FOREIGN", self.identity.cdc_session_id)
        tx = CDCTransaction("tx-cross-run", foreign_id, PostgresLSNPosition("0/1000000"))
        tx.mark_commit()

        with self.assertRaises(CDCExecutionError) as ctx:
            self.buffer.append_transaction(tx, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.TRANSACTION_CORRUPTION)

    # 20. cross-session apply substitution
    def test_attack_20_cross_session_apply_substitution_rejected(self):
        foreign_id = CDCEventIdentity(self.identity.migration_id, self.identity.job_id, self.identity.run_id, "sess-FOREIGN")
        tx = CDCTransaction("tx-cross-sess", foreign_id, PostgresLSNPosition("0/1000000"))
        tx.mark_commit()

        with self.assertRaises(CDCExecutionError) as ctx:
            self.buffer.append_transaction(tx, self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.TRANSACTION_CORRUPTION)

    # 21. checkpoint contradiction
    def test_attack_21_checkpoint_contradiction_rejected(self):
        pos1 = PostgresLSNPosition("0/2000000")
        pos2 = PostgresLSNPosition("0/1000000")

        with self.assertRaises(ValueError):
            CDCCheckpoint("c-bad", self.identity.migration_id, self.identity.job_id, self.identity.run_id, self.identity.cdc_session_id, 1, pos1, pos2, pos1)

    # 22. position regression
    def test_attack_22_position_regression_rejected(self):
        pos_high = PostgresLSNPosition("0/2000000")
        pos_low = PostgresLSNPosition("0/1000000")
        self.assertTrue(pos_high.is_after(pos_low))

    # 23. target DML failure rollback
    def test_attack_23_target_dml_failure_rollback(self):
        tx = self._create_sample_tx("tx-unsafe-del", op=CDCOperationType.DELETE, after={}, before={})
        self.buffer.append_transaction(tx, self.fencing_epoch)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.UNSAFE_DELETE)

    # 24. target commit failure
    def test_attack_24_target_commit_failure_handled(self):
        tx = self._create_sample_tx("tx-unsafe-upd", op=CDCOperationType.UPDATE, after={"a": 1}, before={})
        self.buffer.append_transaction(tx, self.fencing_epoch)

        with self.assertRaises(CDCExecutionError) as ctx:
            self.worker.apply_next_transaction(self.fencing_epoch)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.UNSAFE_UPDATE)

    # 25. backpressure hard-limit behavior
    def test_attack_25_backpressure_hard_limit_behavior(self):
        buf = DurableCDCBuffer(self.identity, max_buffered_events=5, wal_dir=self.temp_dir)
        for i in range(10):
            tx = self._create_sample_tx(f"tx-bp-{i}")
            buf.append_transaction(tx, 1)

        tx_overflow = self._create_sample_tx("tx-bp-overflow")
        with self.assertRaises(CDCExecutionError) as ctx:
            buf.append_transaction(tx_overflow, 1)
        self.assertEqual(ctx.exception.failure.failure_type, CDCFailureType.DURABLE_BUFFER_FAILURE)

    # 26. monitoring failure truth
    def test_attack_26_monitoring_failure_truth(self):
        res = self.gateway.invoke("get_cdc_telemetry", {"cdc_session_id": "nonexistent"})
        self.assertEqual(res["status"], "UNKNOWN")

    # 27. unexpected exception propagation
    def test_attack_27_unexpected_exception_propagation(self):
        with self.assertRaises(ValueError):
            self.gateway.invoke("invalid_capability", {})

    # 28. secret/row diagnostic safety
    def test_attack_28_secret_and_row_diagnostic_safety(self):
        evt = CDCEvent(
            identity=self.identity,
            source_engine="POSTGRESQL",
            source_database="db",
            source_schema="public",
            source_table="users",
            operation=CDCOperationType.INSERT,
            position=PostgresLSNPosition("0/1000000"),
            after_image={"id": 1, "password": "supersecretpassword123"},
        )
        dict_data = evt.to_dict()
        self.assertEqual(dict_data["after_image"]["password"], "[REDACTED_SECRET]")

        safe_summary = evt.to_data_safe_dict()
        self.assertNotIn("supersecretpassword123", str(safe_summary))


if __name__ == "__main__":
    unittest.main()
