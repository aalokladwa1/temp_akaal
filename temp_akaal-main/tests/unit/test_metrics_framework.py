# -*- coding: utf-8 -*-
import asyncio
import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock

from akaal.core.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.models.enums import SystemType, MigrationStrategy
from akaal.core.models.project import ConnectionConfig, MigrationProject, MigrationSession
from akaal.core.observability import ObservabilityContext
from akaal.metrics.registry import MetricsRegistry
from akaal.metrics.constants import (
    MIGRATION_DURATION,
    ROWS_MIGRATED,
    BYTES_MIGRATED,
    TABLES_MIGRATED,
)
from akaal.core.connection_pool.pool import ConnectionPool, get_connection_pool
from akaal.core.loop_governor.governor import LoopGovernor, LoopState, FailureType, FailureReason, LoopDecision
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.storage.base_storage import ICheckpointStorageAdapter


class TestMetricsFrameworkIntegration(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.registry = MetricsRegistry()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # 1. Test ObservabilityContext
    def test_observability_context_creation(self):
        context = ObservabilityContext()
        self.assertIsNotNone(context.registry)
        self.assertIsNone(context.trace)
        self.assertIsInstance(context.registry, MetricsRegistry)

    # 2. Test Registry ownership inside MigrationSession
    def test_session_registry_ownership(self):
        session = MigrationSession(project_id="proj-1")
        self.assertIsNone(session.observability)
        self.assertIsNone(session.metrics_summary)

        context = ObservabilityContext()
        session.observability = context
        self.assertEqual(session.observability.registry, context.registry)

    # 3. Test LoopGovernor (Retry framework)
    async def test_loop_governor_metrics(self):
        registry = MetricsRegistry()
        governor = LoopGovernor(metrics_registry=registry)
        loop_state = governor.get_or_create_state(
            agent_type=SystemType.POSTGRESQL,  # just an enum dummy
            project_id="p1",
            migration_id="m1"
        )
        
        # Trigger a moderate failure which evaluates to LoopDecision.RETRY
        decision = await governor.evaluate(
            loop_state=loop_state,
            current_state_data={"state": "TEST"},
            failure_type=FailureType.MODERATE,
            failure_reason=FailureReason.CONNECTION_LOST
        )
        self.assertEqual(decision, LoopDecision.RETRY)
        
        snapshot = registry.snapshot().data
        # Note: registry keys are (name, labels)
        retry_key = ("loop_retry_count", frozenset())
        self.assertIn(retry_key, snapshot)
        self.assertEqual(snapshot[retry_key], 1)

    # 4. Test ConnectionPool
    async def test_connection_pool_metrics(self):
        # Create a mock config
        config = MagicMock()
        config.system_type = SystemType.MYSQL
        config.enable_connection_pooling = True
        config.minimum_pool_size = 0
        config.maximum_pool_size = 2
        config.connection_idle_timeout = 60.0
        config.acquisition_timeout = 5.0
        
        # Attach registry
        registry = MetricsRegistry()
        config._metrics = registry

        # Mock adapter
        adapter_instance = MagicMock()
        adapter_instance.create_connection = AsyncMock(return_value="conn1")
        adapter_instance.close_connection = AsyncMock()
        adapter_instance.validate_connection = AsyncMock(return_value=True)

        # Patch adapter registration
        from unittest.mock import patch
        with patch("akaal.core.connection_pool.pool.get_adapter_class", return_value=lambda cfg: adapter_instance):
            pool = ConnectionPool(config)
            conn = await pool.acquire()
            self.assertEqual(conn, "conn1")
            await pool.release(conn)

        snapshot = registry.snapshot().data
        self.assertEqual(snapshot.get(("pool_connection_create_count", frozenset())), 1)
        self.assertEqual(snapshot.get(("pool_acquire_count", frozenset())), 1)
        self.assertEqual(snapshot.get(("pool_release_count", frozenset())), 1)

    # 5. Test CheckpointManager
    async def test_checkpoint_manager_metrics(self):
        storage = MagicMock(spec=ICheckpointStorageAdapter)
        storage.write = AsyncMock(return_value=True)
        storage.read_latest = AsyncMock(return_value=None)
        storage.delete = AsyncMock(return_value=True)

        registry = MetricsRegistry()
        manager = CheckpointManager(storage_adapter=storage, metrics_registry=registry)

        record = CheckpointRecord(
            checkpoint_id="chk1",
            project_id="p1",
            migration_id="m1",
            workflow_state=MigrationStrategy.BIG_BANG,
            table_name="t1",
            batch_number=1,
            worker_id="w1"
        )
        
        # Save progress
        save_ok = await manager.save_progress(record)
        self.assertTrue(save_ok)

        # Purge
        storage.list_by_migration = AsyncMock(return_value=[record])
        record.status = CheckpointStatus.COMPLETED
        purged = await manager.purge("p1", "m1")
        self.assertEqual(purged, 1)

        snapshot = registry.snapshot().data
        self.assertEqual(snapshot.get(("checkpoint_save_count", frozenset())), 1)
        self.assertEqual(snapshot.get(("checkpoint_purge_count", frozenset())), 1)

    # 6. Concurrency: Singleton-per-key initialization validation
    def test_concurrent_first_time_registration(self):
        import concurrent.futures
        registry = MetricsRegistry()
        metric_instances = []

        def get_metric():
            # Request same metric name + labels concurrently
            return registry.counter("concurrent.metric", {"shard": "A"})

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(get_metric) for _ in range(50)]
            for fut in concurrent.futures.as_completed(futures):
                metric_instances.append(fut.result())

        # Assert all threads received the exact same metric instance
        first_instance = metric_instances[0]
        for instance in metric_instances:
            self.assertIs(instance, first_instance)

    # 7. Memory Validation: Bounded Histogram reservoir
    def test_histogram_memory_bound(self):
        registry = MetricsRegistry()
        histogram = registry.histogram("bounded.histogram", reservoir_size=10)
        
        # Record 100 observations
        for i in range(100):
            histogram.record(float(i))
            
        snapshot = histogram.snapshot()
        self.assertEqual(snapshot["count"], 100)
        self.assertEqual(len(snapshot["samples"]), 10)  # Bounded at 10

    # 8. Reset Semantics Validation
    def test_registry_reset(self):
        registry = MetricsRegistry()
        registry.counter("test.c1")
        registry.gauge("test.g1")
        
        self.assertEqual(len(registry.snapshot().data), 2)
        
        # Reset
        registry.reset()
        self.assertEqual(len(registry.snapshot().data), 0)

    # 9. Edge Cases & Safety Constraints
    def test_metrics_edge_cases(self):
        registry = MetricsRegistry()
        
        # Counter: Negative increment should raise ValueError
        c1 = registry.counter("edge.c1")
        with self.assertRaises(ValueError):
            c1.increment(-5)
            
        # Gauge: NaN and Infinity values
        g1 = registry.gauge("edge.g1")
        g1.set(float('nan'))
        import math
        self.assertTrue(math.isnan(g1.get()))
        
        g1.set(float('inf'))
        self.assertEqual(g1.get(), float('inf'))
        
        # Timer: Zero duration
        histogram = registry.histogram("edge.h1")
        from akaal.metrics.metrics import Timer
        timer = Timer(histogram)
        
        # Directly mock/measure elapsed time
        import unittest.mock
        with unittest.mock.patch("time.perf_counter", side_effect=[1.0, 1.0]):
            with timer:
                pass
                
        snapshot = histogram.snapshot()
        self.assertEqual(snapshot["count"], 1)
        self.assertEqual(snapshot["samples"][0], 0.0)  # Zero duration

    # 10. Snapshot Immutability Validation
    def test_snapshot_immutability(self):
        registry = MetricsRegistry()
        registry.counter("test.c1").increment(10)
        
        snapshot = registry.snapshot()
        
        # Attempting to mutate the snapshot mapping must raise TypeError
        with self.assertRaises(TypeError):
            snapshot.data[("test.c1", frozenset())] = 20
            
        # Verify nested structures are also copied and protected
        registry.counter("test.c1").increment(5)
        self.assertEqual(snapshot.data[("test.c1", frozenset())], 10)  # Snapshot value remains unchanged


if __name__ == "__main__":
    unittest.main()
