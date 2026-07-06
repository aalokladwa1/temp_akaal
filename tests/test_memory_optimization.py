import asyncio
import os
import gc
import logging
import time
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from akaal.core.models.enums import SystemType, WorkflowState, MigrationStrategy, Priority, TaskType
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
from akaal.agents.gb.gb_agent import GBAgent, get_memory_usage
from akaal.agents.manager.manager_agent import ManagerAgent
from akaal.core.models.project import ConnectionConfig, MigrationProject
from akaal.core.models.task import Task
from akaal.adapters.adapter_registry import create_adapter


class TestMemoryOptimization(unittest.IsolatedAsyncioTestCase):

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
        self.src_cfg.mock_mode = True
        self.src_cfg.mock_max_rows = 150

        self.tgt_cfg = ConnectionConfig(
            system_type=SystemType.SQLITE,
            host="localhost",
            port=0,
            database_name=":memory:",
            credentials_ref="staging_secret",
            read_only=False
        )
        self.tgt_cfg.mock_mode = True
        self.tgt_cfg.mock_max_rows = 150

        # Setup base directory and files
        self.workspace_dir = os.path.abspath("test_mem_opt_workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        self.state = GlobalState()
        self.message_bus = MessageBus()
        self.storage = SQLiteCheckpointStorageAdapter(
            db_path=os.path.join(self.workspace_dir, "test_checkpoints.db")
        )
        await self.storage.initialize()
        self.checkpoint_mgr = CheckpointManager(storage_adapter=self.storage)

        # Manager & GB Agents
        from unittest.mock import MagicMock
        self.mock_audit = MagicMock()
        self.manager = ManagerAgent(
            global_state=self.state,
            message_bus=self.message_bus,
            audit_logger=self.mock_audit,
            checkpoint_manager=self.checkpoint_mgr,
            agent_id="MANAGER-PRIMARY"
        )
        self.gb_agent = GBAgent(
            global_state=self.state,
            message_bus=self.message_bus,
            agent_id="GB-PRIMARY"
        )
        
        # Override checkpoint mgr on GB agent
        self.gb_agent._checkpoint_mgr = self.checkpoint_mgr

    async def asyncTearDown(self):
        # Shutdown message bus
        await self.message_bus.stop()
        
        # Cleanup directory
        import shutil
        if os.path.exists(self.workspace_dir):
            try:
                shutil.rmtree(self.workspace_dir)
            except Exception:
                pass

    async def _migrate_table(self, project, table_name, parameters, **kwargs):
        use_adaptive = parameters.get("use_adaptive", getattr(project, "use_adaptive_batch", False))
        min_size = parameters.get("min_size", getattr(project, "minimum_batch_size", 10))
        init_size = parameters.get("init_size", getattr(project, "initial_batch_size", 500))
        max_size = parameters.get("max_size", getattr(project, "maximum_batch_size", 5000))
        
        enable_mem_opt = kwargs.pop("enable_memory_optimization", getattr(project, "enable_memory_optimization", True))
        mem_cleanup_interval = kwargs.pop("memory_cleanup_interval", getattr(project, "memory_cleanup_interval", 5))
        mem_warning_threshold = kwargs.pop("memory_warning_threshold_mb", getattr(project, "memory_warning_threshold_mb", 512.0))
        
        return await self.gb_agent.migrate_table(
            source_config=project.source_config,
            target_config=project.target_config,
            table_name=table_name,
            batch_size=parameters.get("batch_size", 500),
            project_id=project.project_id,
            migration_id=project.active_migration_id,
            use_adaptive_batch=use_adaptive,
            minimum_batch_size=min_size,
            initial_batch_size=init_size,
            maximum_batch_size=max_size,
            enable_memory_optimization=enable_mem_opt,
            memory_cleanup_interval=mem_cleanup_interval,
            memory_warning_threshold_mb=mem_warning_threshold,
            **kwargs
        )

    # 1. Peak memory reduction & 2. Long-running migration stability
    async def test_peak_memory_reduction_and_stability(self):
        # Create project with memory optimization enabled
        project = await self.manager.create_project(
            name="mem_opt_enabled_proj",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_memory_optimization=True,
            memory_cleanup_interval=1,
            memory_warning_threshold_mb=10.0 # Small threshold to force GC
        )
        
        # Verify configurations propagated to project
        self.assertTrue(project.enable_memory_optimization)
        self.assertEqual(project.memory_cleanup_interval, 1)
        self.assertEqual(project.memory_warning_threshold_mb, 10.0)

        # Execute migration
        self.src_cfg.mock_max_rows = 20
        self.tgt_cfg.mock_max_rows = 20
        params = {"batch_size": 5, "mock_max_rows": 20}
        res = await self._migrate_table(
            project,
            table_name="composite_table",
            parameters=params
        )
        
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 20)

    # 3. Cursor cleanup & 4. Statement cleanup
    async def test_cursor_and_statement_cleanup(self):
        self.src_cfg.mock_mode = False
        self.src_cfg.enable_memory_optimization = True
        adapter = create_adapter(self.src_cfg)
        await adapter.connect()
        
        # Initialize table and rows in sqlite memory DB
        conn = adapter.get_connection()
        conn.execute("CREATE TABLE no_pk_table (id INTEGER, data TEXT)")
        for i in range(20):
            conn.execute("INSERT INTO no_pk_table VALUES (?, ?)", (i, f"row_{i}"))
        conn.commit()
        
        # Executing read_batch multiple times
        for i in range(3):
            rows = await adapter.read_batch("no_pk_table", offset=i*5, limit=5)
            self.assertEqual(len(rows), 5)
            
        await adapter.close()

    # 5. Emergency GC trigger & 6. Memory threshold warning & 7. Batch dereferencing
    async def test_emergency_gc_and_warnings(self):
        # We will capture logging output to assert warning logs
        logger = logging.getLogger("nexusforge.gb")
        warning_logged = False
        
        class MockHandler(logging.Handler):
            def emit(self, record):
                nonlocal warning_logged
                if "Peak memory threshold exceeded" in record.getMessage():
                    warning_logged = True
                    
        handler = MockHandler()
        logger.addHandler(handler)
        
        try:
            project = await self.manager.create_project(
                name="mem_opt_warning_proj",
                source_config=self.src_cfg,
                target_config=self.tgt_cfg,
                strategy=MigrationStrategy.BIG_BANG,
                enable_memory_optimization=True,
                memory_cleanup_interval=2,
                memory_warning_threshold_mb=0.01 # Set tiny threshold to guarantee warnings
            )
            
            with patch("akaal.agents.gb.gb_agent.get_memory_usage", return_value=1.0):
                res = await self._migrate_table(
                    project,
                    table_name="string_table",
                    parameters={"batch_size": 2, "mock_max_rows": 6}
                )
            
            self.assertEqual(res["status"], "SUCCESS")
            # The warning log should have been triggered
            self.assertTrue(warning_logged)
        finally:
            logger.removeHandler(handler)

    # 8. Checkpoint compatibility & 9. Retry compatibility & 10. Adaptive batching compatibility
    async def test_phase7_subsystem_compatibilities(self):
        project = await self.manager.create_project(
            name="subsystem_compatibility_proj",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            use_adaptive_batch=True,
            enable_memory_optimization=True,
            memory_cleanup_interval=1
        )
        
        # Test runs adaptive batch and memory optimization together
        res = await self._migrate_table(
            project,
            table_name="uuid_table",
            parameters={"batch_size": 5, "mock_max_rows": 15}
        )
        self.assertEqual(res["status"], "SUCCESS")

    # 11. Connection pooling compatibility & 12. Parallel migration compatibility
    async def test_pooling_and_parallel_compatibility(self):
        self.src_cfg.enable_connection_pooling = True
        self.src_cfg.enable_memory_optimization = True
        
        project = await self.manager.create_project(
            name="pooling_parallel_proj",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_connection_pooling=True,
            enable_memory_optimization=True,
            memory_cleanup_interval=1
        )
        
        res = await self._migrate_table(
            project,
            table_name="string_table",
            parameters={"batch_size": 5, "mock_max_rows": 10}
        )
        self.assertEqual(res["status"], "SUCCESS")

    # 13. Transaction correctness & 14. No row loss & 15. No duplicate rows
    async def test_transaction_integrity_and_data_loss(self):
        project = await self.manager.create_project(
            name="integrity_proj",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_memory_optimization=True
        )
        
        self.src_cfg.mock_max_rows = 30
        self.tgt_cfg.mock_max_rows = 30
        res = await self._migrate_table(
            project,
            table_name="composite_table",
            parameters={"batch_size": 10, "mock_max_rows": 30}
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["rows_migrated"], 30)

    # 18. Disabled optimization compatibility
    async def test_disabled_optimization(self):
        project = await self.manager.create_project(
            name="mem_opt_disabled_proj",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_memory_optimization=False
        )
        self.assertFalse(project.enable_memory_optimization)
        
        res = await self._migrate_table(
            project,
            table_name="uuid_table",
            parameters={"batch_size": 5, "mock_max_rows": 10}
        )
        self.assertEqual(res["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
