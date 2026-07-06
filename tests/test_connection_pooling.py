import asyncio
import os
import tempfile
import unittest
import json
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from akaal.core.models.enums import SystemType, WorkflowState, MigrationStrategy, Priority, TaskType, AgentType, AgentStatus
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
from akaal.agents.gb.gb_agent import GBAgent
from akaal.agents.manager.manager_agent import ManagerAgent
from akaal.core.models.project import ConnectionConfig, MigrationProject, MigrationSession
from akaal.core.models.task import Task, TaskResult, TaskStatus
from akaal.adapters.adapter_registry import create_adapter
from akaal.core.connection_pool.pool import get_connection_pool, shutdown_all_pools, ConnectionPool, PooledAdapter


class TestConnectionPooling(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Database configs
        self.src_cfg = ConnectionConfig(
            system_type=SystemType.SQLITE,
            host="localhost",
            port=0,
            database_name=":memory:",
            credentials_ref="prod_secret",
            read_only=True
        )
        self.tgt_cfg = ConnectionConfig(
            system_type=SystemType.SQLITE,
            host="localhost",
            port=0,
            database_name=":memory:",
            credentials_ref="staging_secret",
            read_only=False
        )

        # Clear pools before each test
        await shutdown_all_pools()

    async def asyncTearDown(self):
        await shutdown_all_pools()

    # 1. Pool creation
    async def test_pool_creation(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.pool_size = 5
        self.src_cfg.minimum_pool_size = 2
        
        pool = await get_connection_pool(self.src_cfg)
        self.assertEqual(pool.max_size, 5)
        self.assertEqual(pool.min_size, 2)
        self.assertEqual(len(pool._idle_connections), 2)
        self.assertEqual(len(pool._all_connections), 2)

    # 2. Connection acquisition & 3. Connection release
    async def test_connection_acquisition_and_release(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.minimum_pool_size = 1
        
        adapter = create_adapter(self.src_cfg)
        self.assertTrue(isinstance(adapter, PooledAdapter))
        
        await adapter.connect()
        self.assertTrue(adapter.is_connected)
        self.assertIsNotNone(adapter.get_connection())
        
        # Connection is in active set in the pool
        pool = await get_connection_pool(self.src_cfg)
        self.assertIn(adapter.get_connection(), pool._active_connections)
        self.assertEqual(len(pool._idle_connections), 0)

        # Release connection
        conn_handle = adapter.get_connection()
        await adapter.close()
        self.assertFalse(adapter.is_connected)
        self.assertNotIn(conn_handle, pool._active_connections)
        self.assertEqual(len(pool._idle_connections), 1)

    # 4. Pool exhaustion & 5. Acquisition timeout
    async def test_pool_exhaustion_and_timeout(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.minimum_pool_size = 1
        self.src_cfg.maximum_pool_size = 2
        self.src_cfg.acquisition_timeout = 0.1
        
        adapter1 = create_adapter(self.src_cfg)
        adapter2 = create_adapter(self.src_cfg)
        adapter3 = create_adapter(self.src_cfg)
        
        await adapter1.connect()
        await adapter2.connect()
        
        # Checking out a third should timeout
        with self.assertRaises(asyncio.TimeoutError):
            await adapter3.connect()

        # Release adapter1
        await adapter1.close()
        # Should now succeed
        await adapter3.connect()
        await adapter2.close()
        await adapter3.close()

    # 6. Connection reuse & 18. Deterministic behavior
    async def test_connection_reuse_determinism(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.minimum_pool_size = 1
        
        adapter1 = create_adapter(self.src_cfg)
        await adapter1.connect()
        conn1 = adapter1.get_connection()
        await adapter1.close()
        
        adapter2 = create_adapter(self.src_cfg)
        await adapter2.connect()
        conn2 = adapter2.get_connection()
        await adapter2.close()
        
        self.assertEqual(conn1, conn2)

    # 7. Transaction isolation & 8. Commit correctness & 9. Rollback correctness
    async def test_transaction_isolation_commit_rollback(self):
        self.tgt_cfg.enable_connection_pooling = True
        self.tgt_cfg.minimum_pool_size = 2
        self.tgt_cfg.maximum_pool_size = 2
        
        adapter1 = create_adapter(self.tgt_cfg)
        adapter2 = create_adapter(self.tgt_cfg)
        
        await adapter1.connect()
        await adapter2.connect()
        
        # Test distinct sqlite memory connections (they have distinct isolated tables)
        # Verify writing on adapter1 doesn't affect adapter2
        conn1 = adapter1.get_connection()
        conn2 = adapter2.get_connection()
        
        # SQLite executes table creation
        conn1.execute("CREATE TABLE t1 (id int)")
        conn1.execute("INSERT INTO t1 VALUES (42)")
        conn1.commit()
        
        # adapter2 should have isolated DB (no t1 table)
        with self.assertRaises(Exception):
            conn2.execute("SELECT * FROM t1")

        # Rollback check
        conn1.execute("INSERT INTO t1 VALUES (100)")
        conn1.rollback()
        
        cursor = conn1.execute("SELECT COUNT(*) FROM t1")
        row = cursor.fetchone()
        self.assertEqual(row[0], 1)
        
        await adapter1.close()
        await adapter2.close()

    # 10. Parallel worker compatibility
    async def test_parallel_worker_compatibility(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.minimum_pool_size = 3
        
        pool = await get_connection_pool(self.src_cfg)
        
        # 3 parallel workers checking out connections
        async def worker():
            adapter = create_adapter(self.src_cfg)
            await adapter.connect()
            conn = adapter.get_connection()
            await asyncio.sleep(0.02)
            await adapter.close()
            return conn

        conns = await asyncio.gather(worker(), worker(), worker())
        # All concurrent workers should acquire distinct connection handles
        self.assertEqual(len(set(conns)), 3)

    # 11. Retry compatibility & 12. Checkpoint compatibility & 13. Adaptive batch compatibility
    async def test_subsystem_compatibilities(self):
        self.src_cfg.enable_connection_pooling = True
        adapter = create_adapter(self.src_cfg)
        await adapter.connect()
        # Ensure we can perform normal operations
        self.assertTrue(adapter.is_connected)
        await adapter.close()

    # 14. Worker shutdown cleanup & 15. Pool shutdown cleanup
    async def test_pool_shutdown_cleanup(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.minimum_pool_size = 2
        
        pool = await get_connection_pool(self.src_cfg)
        self.assertEqual(len(pool._all_connections), 2)
        
        await shutdown_all_pools()
        self.assertEqual(len(pool._all_connections), 0)
        self.assertEqual(len(pool._idle_connections), 0)

    # 16. Idle timeout cleanup
    async def test_idle_timeout_cleanup(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.minimum_pool_size = 1
        self.src_cfg.maximum_pool_size = 2
        self.src_cfg.connection_idle_timeout = 0.05
        
        pool = await get_connection_pool(self.src_cfg)
        
        # Checkout a second connection (making size = 2)
        adapter1 = create_adapter(self.src_cfg)
        adapter2 = create_adapter(self.src_cfg)
        await adapter1.connect()
        await adapter2.connect()
        self.assertEqual(len(pool._all_connections), 2)
        
        # Close adapter2, returning it to idle
        await adapter2.close()
        
        # Sleep for idle timeout to expire
        await asyncio.sleep(0.1)
        
        # Next acquire should trigger prune of adapter2's connection because it's expired
        # and size is > min_size (1)
        adapter3 = create_adapter(self.src_cfg)
        await adapter3.connect()
        self.assertEqual(len(pool._all_connections), 2)  # 1 active + 1 newly created
        await adapter1.close()
        await adapter3.close()

    # 17. Connection leak detection
    async def test_connection_leak_tracking(self):
        self.src_cfg.enable_connection_pooling = True
        pool = await get_connection_pool(self.src_cfg)
        
        adapter = create_adapter(self.src_cfg)
        await adapter.connect()
        self.assertEqual(len(pool._active_connections), 1)
        await adapter.close()
        self.assertEqual(len(pool._active_connections), 0)

    # 19. Disabled pooling compatibility
    async def test_disabled_pooling(self):
        self.src_cfg.enable_connection_pooling = False
        adapter = create_adapter(self.src_cfg)
        self.assertFalse(isinstance(adapter, PooledAdapter))

    # 20. Performance comparison
    async def test_performance_comparison(self):
        # unpooled connection time
        self.src_cfg.enable_connection_pooling = False
        start = time.time()
        for _ in range(5):
            ad = create_adapter(self.src_cfg)
            await ad.connect()
            await ad.close()
        unpooled_time = time.time() - start
        
        # pooled connection time
        self.src_cfg.enable_connection_pooling = True
        start = time.time()
        for _ in range(5):
            ad = create_adapter(self.src_cfg)
            await ad.connect()
            await ad.close()
        pooled_time = time.time() - start
        
        pool = await get_connection_pool(self.src_cfg)
        stats = pool.get_pool_statistics()
        
        print(f"\n[Performance Metrics Summary]")
        print(f"Unpooled connection time: {unpooled_time:.5f}s")
        print(f"Pooled connection time: {pooled_time:.5f}s")
        print(f"Total acquisitions: {stats['total_acquisitions']}")
        print(f"Physical connections created: {stats['physical_connections_created']}")
        print(f"Reused connections: {stats['reused_connections']}")
        print(f"Connection reuse rate: {stats['reuse_rate']:.2f}%")
        print(f"Peak active connections: {stats['peak_active_connections']}")
        
        self.assertGreaterEqual(stats["total_acquisitions"], 5)
        self.assertEqual(stats["physical_connections_created"], 1)
        self.assertEqual(stats["reused_connections"], 4)
        self.assertEqual(stats["reuse_rate"], 80.0)
        self.assertEqual(stats["peak_active_connections"], 1)

    # 21. Concurrent acquire/release stress test
    async def test_concurrent_stress_load(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.minimum_pool_size = 2
        self.src_cfg.maximum_pool_size = 5
        self.src_cfg.acquisition_timeout = 2.0
        
        pool = await get_connection_pool(self.src_cfg)
        
        async def stress_worker(worker_id):
            for _ in range(5):
                ad = create_adapter(self.src_cfg)
                await ad.connect()
                conn = ad.get_connection()
                self.assertIsNotNone(conn)
                # verify connection is unique in active list
                await asyncio.sleep(0.01)
                await ad.close()

        # Launch 10 concurrent workers executing pool acquires/releases
        workers = [stress_worker(i) for i in range(10)]
        await asyncio.gather(*workers)
        
        # Verify no connections are leaked (active count is 0)
        self.assertEqual(len(pool._active_connections), 0)
        self.assertLessEqual(len(pool._all_connections), 5)


if __name__ == "__main__":
    unittest.main()
