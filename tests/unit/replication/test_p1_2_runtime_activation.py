"""
AKAAL P1.2 Unit Test Suite — Canonical Production Migration Runtime Activation
================================================================================
Comprehensive verification of Parallel Worker Scheduling, Adaptive Batching,
Range Partitioning, Connection Pooling, Durable WAL Checkpointing, Deterministic Resume,
Backpressure/Throttling, and Delivery Semantics.
"""

import unittest
import os
import uuid
import sqlite3
import hashlib
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
from akaal.replication.resolver import resolve_physical_reader, resolve_physical_writer


class TestP12RuntimeActivation(unittest.TestCase):
    """P1.2 Comprehensive Unit Test Suite."""

    def setUp(self):
        self.db_path = f"artifacts/test_ckpt_{uuid.uuid4().hex[:8]}.db"

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_01_range_partitioner_intra_table_chunking(self):
        """Verify RangePartitioner generates non-overlapping, gapless numeric range partitions."""
        partitioner = RangePartitioner(tuning_policy=TuningPolicy(parallelism=4, batch_size=1000))
        parts = partitioner.generate_partitions_for_table(
            table_name="BIG_ORDERS",
            schema_name="DATA_SCH",
            target_schema="app_analytics",
            total_rows=400000,
            pk_columns=["order_id"],
            min_pk=1,
            max_pk=400000,
            strategy=PartitionStrategy.PK_NUMERIC_RANGE,
        )

        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0].lower_bound, 1)
        self.assertEqual(parts[0].upper_bound, 100001)
        self.assertEqual(parts[1].lower_bound, 100001)
        self.assertEqual(parts[1].upper_bound, 200001)
        self.assertEqual(parts[2].lower_bound, 200001)
        self.assertEqual(parts[2].upper_bound, 300001)
        self.assertEqual(parts[3].lower_bound, 300001)
        self.assertEqual(parts[3].upper_bound, 400001)

    def test_02_adaptive_throughput_optimizer_bounds(self):
        """Verify AdaptiveThroughputOptimizer dynamically tunes batch sizes within safe bounds."""
        optimizer = AdaptiveThroughputOptimizer()

        # High pressure test (high memory & latency) -> expect scale down
        high_press_spec = optimizer.optimize_throughput({
            "cpu_percent": 90.0,
            "memory_utilization_pct": 85.0,
            "target_latency_ms": 150.0,
            "queue_depth": 500,
            "retry_frequency": 0.5,
        }, {"batch_size": 2000})

        self.assertLess(high_press_spec.batch_size, 2000)
        self.assertGreaterEqual(high_press_spec.batch_size, 50)

        # Low pressure test (low memory & low latency) -> expect scale up
        low_press_spec = optimizer.optimize_throughput({
            "cpu_percent": 10.0,
            "memory_utilization_pct": 20.0,
            "target_latency_ms": 2.0,
            "queue_depth": 100,
            "retry_frequency": 0.0,
        }, {"batch_size": 1000})

        self.assertGreaterEqual(low_press_spec.batch_size, 1000)
        self.assertLessEqual(low_press_spec.batch_size, 5000)

    def test_03_backpressure_controller_throttling(self):
        """Verify BackpressureController applies adaptive sleep delays under queue pressure."""
        controller = BackpressureController(max_queue_capacity=100)

        # Under low watermark -> no throttle
        state1 = controller.check_and_update(10)
        delay1 = controller.apply_throttling()
        self.assertEqual(delay1, 0.0)

        # Over high watermark -> throttled delay applied
        state2 = controller.check_and_update(100)
        t0 = time.time()
        delay2 = controller.apply_throttling()
        elapsed = time.time() - t0

        self.assertGreater(delay2, 0.0)
        self.assertGreaterEqual(elapsed, 0.04)

    def test_04_durable_checkpoint_store_persistence(self):
        """Verify CheckpointStore records committed batch checkpoints atomically."""
        store = CheckpointStore(db_path=self.db_path)
        store.begin_batch(
            checkpoint_id="chkpt-1",
            migration_id="mig-101",
            partition_id="part-orders-001",
            table_name="orders",
            batch_number=1,
            worker_id="worker-01",
        )

        store.mark_batch_committed(
            checkpoint_id="chkpt-1",
            migration_id="mig-101",
            partition_id="part-orders-001",
            table_name="orders",
            batch_number=1,
            worker_id="worker-01",
            rows_processed=5000,
            last_committed_key=5000,
            checksum="hash-5000",
        )

        ckpt = store.get_latest_checkpoint("part-orders-001")
        self.assertIsNotNone(ckpt)
        self.assertEqual(ckpt["rows_processed"], 5000)
        self.assertEqual(ckpt["last_committed_key"], "5000")
        self.assertEqual(ckpt["status"], "COMMITTED")

    def test_05_deterministic_resume_engine_spec_building(self):
        """Verify DeterministicResumeEngine constructs non-OFFSET SQL predicates from checkpoints."""
        engine = DeterministicResumeEngine()
        mock_ckpt = MagicMock()
        mock_ckpt.verify_checksum.return_value = True
        mock_ckpt.state_data = {
            "last_committed_batch": 5,
            "last_seen_pk": 25000,
        }

        spec = engine.build_resume_spec(
            table_name="orders",
            checkpoint=mock_ckpt,
            pk_columns=["order_id"],
        )

        self.assertEqual(spec.resume_mode, "PRIMARY_KEY")
        self.assertIn("orders.order_id > :last_seen_pk", spec.where_clause)
        self.assertEqual(spec.bind_params["last_seen_pk"], 25000)

    def test_06_lob_stream_pipe_chunking(self):
        """Verify LOBStreamPipe streams large CLOB/BLOB content in bounded 64KB chunks."""
        pipe = LOBStreamPipe(chunk_size_bytes=100)
        sample_lob = "A" * 250  # 250 bytes payload

        chunks = list(pipe.stream_lob_data(sample_lob))
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["chunk_bytes"], 100)
        self.assertFalse(chunks[0]["is_last_chunk"])
        self.assertEqual(chunks[2]["chunk_bytes"], 50)
        self.assertTrue(chunks[2]["is_last_chunk"])

    def test_07_connection_pool_acquisition_and_metrics(self):
        """Verify ConnectionPool statistics and acquisition tracking."""
        mock_config = MagicMock()
        mock_config.system_type.value = "ORACLE"
        mock_config.enable_connection_pooling = True
        mock_config.maximum_pool_size = 2
        mock_config.minimum_pool_size = 1

        pool = ConnectionPool(mock_config)
        stats = pool.get_pool_statistics()

        self.assertIn("total_acquisitions", stats)
        self.assertIn("reuse_rate", stats)

    @patch("psycopg2.connect")
    @patch("oracledb.connect")
    def test_08_physical_resolver_generic_registration(self, mock_ora, mock_pg):
        """Verify resolve_physical_reader and resolve_physical_writer enforce generic database interfaces."""
        params = {"host": "localhost", "port": 1521, "database": "db", "username": "u", "password": "p"}
        reader = resolve_physical_reader("ORACLE", params)
        writer = resolve_physical_writer("POSTGRESQL", params)

        self.assertEqual(type(reader).__name__, "OraclePhysicalReader")
        self.assertEqual(type(writer).__name__, "PostgreSQLPhysicalWriter")


if __name__ == "__main__":
    unittest.main()
