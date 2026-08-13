"""
AKAAL P1.2.1 Verification Suite — Production Runtime Proof, Failure-Semantics & Reachability
==============================================================================================
Forensic verification and hardening tests for WF-011 execution path, Connection Pooling,
WAL Checkpointing, Failure Semantics, Adaptive Batching, and Secret Protection.
"""

import unittest
import os
import uuid
import sqlite3
import time
from unittest.mock import MagicMock, patch

from akaal.replication.scheduling.parallel_scheduler import (
    ParallelReplicationScheduler,
    worker_process_partition_task_canonical,
)
from akaal.engine.spec import TransportPartition, PartitionStrategy, TuningPolicy
from akaal.replication.partitioning.range_partitioner import RangePartitioner
from akaal.performance.optimizers.throughput import AdaptiveThroughputOptimizer
from akaal.streaming.flow.backpressure import BackpressureController
from akaal.replication.checkpointing.checkpoint_store import CheckpointStore
from akaal.core.connection_pool.pool import ConnectionPool, PooledAdapter
from akaal.migration.execution.resume_engine import DeterministicResumeEngine
from akaal.streaming.lob.lob_pipeline import LOBStreamPipe
from akaal.replication.writers.postgresql_writer import PostgreSQLPhysicalWriter
from akaal.core.state.state_store import CentralStateStore


class TestP121RuntimeProof(unittest.TestCase):
    """P1.2.1 Comprehensive Verification & Proof Suite."""

    def setUp(self):
        self.db_path = f"artifacts/test_ckpt_p121_{uuid.uuid4().hex[:8]}.db"

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_01_production_connection_failure_cannot_fallback_to_mock(self):
        """Invariant: Real PostgreSQL connection failure MUST raise OperationalError and NEVER fall back to mock."""
        params = {
            "host": "127.0.0.1",
            "port": 5433,  # Invalid port to trigger failure
            "database": "nonexistent_db",
            "username": "invalid_user",
            "password": "wrong_password",
            "allow_mock_fallback": False,
        }

        with patch("psycopg2.connect") as mock_connect:
            import psycopg2
            mock_connect.side_effect = psycopg2.OperationalError("connection failed")

            with self.assertRaises(psycopg2.OperationalError):
                PostgreSQLPhysicalWriter(params)

    def test_02_explicit_test_mock_fallback_allowed_only_when_flagged(self):
        """Verify mock fallback is permitted ONLY when allow_mock_fallback=True is explicitly passed."""
        params = {
            "host": "127.0.0.1",
            "port": 5433,
            "database": "db",
            "username": "u",
            "password": "p",
            "allow_mock_fallback": True,
        }

        with patch("psycopg2.connect") as mock_connect:
            import psycopg2
            mock_connect.side_effect = psycopg2.OperationalError("connection failed")

            writer = PostgreSQLPhysicalWriter(params)
            self.assertIsNotNone(writer.conn)
            self.assertTrue(isinstance(writer.conn, MagicMock))

    def test_03_commit_before_checkpoint_ordering(self):
        """Verify target database transaction commit strictly precedes WAL checkpoint advancement."""
        store = CheckpointStore(db_path=self.db_path)

        # 1. Begin batch
        store.begin_batch(
            checkpoint_id="chkpt-batch-001",
            migration_id="mig-proof-100",
            partition_id="part-100",
            table_name="orders",
            batch_number=1,
            worker_id="worker-01",
        )

        # Before commit: latest committed checkpoint should be None
        self.assertIsNone(store.get_latest_checkpoint("part-100"))

        # 2. Mark committed (simulating post-writer.commit())
        store.mark_batch_committed(
            checkpoint_id="chkpt-batch-001",
            migration_id="mig-proof-100",
            partition_id="part-100",
            table_name="orders",
            batch_number=1,
            worker_id="worker-01",
            rows_processed=1000,
            last_committed_key=1000,
            checksum="hash-1000",
        )

        # After commit: latest committed checkpoint is available
        ckpt = store.get_latest_checkpoint("part-100")
        self.assertIsNotNone(ckpt)
        self.assertEqual(ckpt["status"], "COMMITTED")
        self.assertEqual(ckpt["last_committed_key"], "1000")

    def test_04_daemon_restart_state_reconstruction(self):
        """Verify CentralStateStore state survives re-instantiation across daemon restarts."""
        state_store_1 = CentralStateStore()
        mig_id = f"mig-test-{uuid.uuid4().hex[:6]}"

        state_store_1.update_progress(mig_id, {
            "status": "RUNNING",
            "rows_migrated": 50000,
            "total_tables": 5028,
            "current_stage": "transport",
        })

        # Re-instantiate CentralStateStore (simulating daemon restart)
        state_store_2 = CentralStateStore()
        progress = state_store_2._state.get("progress", {}).get(mig_id)

        self.assertIsNotNone(progress)
        self.assertEqual(progress["status"], "RUNNING")
        self.assertEqual(progress["rows_migrated"], 50000)
        self.assertEqual(progress["current_stage"], "transport")

    def test_05_plaintext_secrets_exclusion_in_checkpoints(self):
        """Verify no plaintext passwords or secrets enter CheckpointStore WAL database."""
        store = CheckpointStore(db_path=self.db_path)
        store.begin_batch("c1", "mig-sec", "part-sec", "users", 1, "w1")
        store.mark_batch_committed("c1", "mig-sec", "part-sec", "users", 1, "w1", 10, "10", "hash1")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM checkpoints WHERE checkpoint_id='c1'")
        row = dict(cursor.fetchone())
        conn.close()

        row_str = str(row).lower()
        self.assertNotIn("password", row_str)
        self.assertNotIn("secret", row_str)
        self.assertNotIn("token", row_str)

    def test_06_parallel_scheduler_worker_exception_propagation(self):
        """Verify worker process exception propagates cleanly to caller without false success."""
        scheduler = ParallelReplicationScheduler(max_workers=2)

        part = TransportPartition(
            partition_id="part-err-01",
            table_name="nonexistent_table",
            schema_name="INVALID_SCH",
            target_schema="public",
            strategy=PartitionStrategy.SINGLE_STREAM,
        )

        src_params = {"system_type": "UNSUPPORTED_TYPE_XYZ", "host": "127.0.0.1", "port": 1521, "database": "db", "username": "u", "password": "p"}
        tgt_params = {"system_type": "POSTGRESQL", "host": "127.0.0.1", "port": 5432, "database": "db", "username": "u", "password": "p"}

        with self.assertRaises(ValueError) as ctx:
            scheduler.execute_partitions([part], src_params, tgt_params, "mig-fail-test")

        self.assertIn("UNSUPPORTED_TYPE_XYZ", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
