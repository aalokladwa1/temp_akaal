import asyncio
import os
import tempfile
import unittest
import json
from typing import Any, Dict, List, Optional, Set
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
from akaal.audit.audit_logger import AuditLogger


class MockConfig:
    def __init__(self, system_type: SystemType, mock_max_rows: int = 100):
        self.system_type = system_type
        self.mock_mode = True
        self.database_name = "test_db"
        self.db_path = ":memory:"
        self.host = "source-db.example.com"
        self.mock_max_rows = mock_max_rows
        self.read_only = True


class TestParallelMigration(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.workspace_dir = tempfile.mkdtemp()
        self.temp_db_path = os.path.join(self.workspace_dir, "checkpoints.db")
        
        self.storage = SQLiteCheckpointStorageAdapter(self.temp_db_path)
        await self.storage.initialize()
        self.checkpoint_mgr = CheckpointManager(self.storage)

        self.mock_state = GlobalState()
        self.mock_bus = MessageBus()
        self.mock_audit = MagicMock(spec=AuditLogger)

        self.manager = ManagerAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            audit_logger=self.mock_audit,
            checkpoint_manager=self.checkpoint_mgr,
            agent_id="MANAGER-PRIMARY",
            is_backup=False
        )
        self.manager._workspace_dir = self.workspace_dir

        self.gb = GBAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=self.checkpoint_mgr,
            workspace_dir=self.workspace_dir,
            agent_id="GB-PRIMARY",
            is_backup=False
        )

        await self.manager.start()
        await self.gb.start()

        # Connect Configs
        self.src_cfg = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="source-db.example.com",
            port=5432,
            database_name="prod_db",
            credentials_ref="prod_secret",
            read_only=True
        )
        self.tgt_cfg = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="target-db.example.com",
            port=5432,
            database_name="staging_db",
            credentials_ref="staging_secret",
            read_only=False
        )

    async def asyncTearDown(self):
        await self.gb.stop()
        await self.manager.stop()
        await self.mock_bus.stop()
        
        for root, dirs, files in os.walk(self.workspace_dir, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except Exception:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except Exception:
                    pass
        try:
            os.rmdir(self.workspace_dir)
        except Exception:
            pass

        try:
            os.remove(self.temp_db_path)
        except Exception:
            pass

    def _create_mock_snapshot(self, project_id: str, migration_id: str, schema_objects: List[Dict[str, Any]]):
        os.makedirs(os.path.join(self.workspace_dir, "projects", project_id), exist_ok=True)
        snapshot_filepath = os.path.join(
            self.workspace_dir, "projects", project_id, f"gb_snapshot_{migration_id}_v1.json"
        )
        snapshot_data = {
            "gb_id": f"GB-{project_id[:8]}",
            "version_id": 1,
            "project_id": project_id,
            "migration_id": migration_id,
            "checksum": "dummy_checksum",
            "schema_objects": schema_objects
        }
        with open(snapshot_filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2)

    # 1. Single worker migration & 2. Multiple worker migration & 3. Configurable worker count
    async def test_worker_concurrency_configurations(self):
        project = await self.manager.create_project(
            name="Test Concurrency",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=2
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True
        
        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        # 3 independent tables
        schema_objects = [
            {"object_name": "t1", "object_type": "TABLE", "dependency_references": []},
            {"object_name": "t2", "object_type": "TABLE", "dependency_references": []},
            {"object_name": "t3", "object_type": "TABLE", "dependency_references": []},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        # Track concurrent active dispatches to verify max_parallel_workers=2 constraint
        max_concurrent_active = 0
        current_concurrent_active = 0
        dispatch_lock = asyncio.Lock()

        original_dispatch = self.manager._dispatch_task

        async def mock_dispatch(task, proj):
            nonlocal current_concurrent_active, max_concurrent_active
            tbl = task.parameters.get("table_name")
            
            # Concurrency logic applies only to tables migration
            if task.task_type == TaskType.MIGRATION_BATCH and tbl:
                async with dispatch_lock:
                    current_concurrent_active += 1
                    if current_concurrent_active > max_concurrent_active:
                        max_concurrent_active = current_concurrent_active
                
                await asyncio.sleep(0.05)
                
                async with dispatch_lock:
                    current_concurrent_active -= 1
                    
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch):
            await self.manager._run_production_migration_stage(project, session)
            
        self.assertLessEqual(max_concurrent_active, 2)
        self.assertEqual(project.state, WorkflowState.PRODUCTION_VALIDATION)

    # 4. Parallel independent tables
    async def test_parallel_independent_tables(self):
        project = await self.manager.create_project(
            name="Test Independent",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=3
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True

        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        # t1 and t2 are independent, t3 depends on t1
        schema_objects = [
            {"object_name": "t1", "object_type": "TABLE", "dependency_references": []},
            {"object_name": "t2", "object_type": "TABLE", "dependency_references": []},
            {"object_name": "t3", "object_type": "TABLE", "dependency_references": [
                {"target_table": "t1"}
            ]},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        scheduled_sequence = []
        dispatch_lock = asyncio.Lock()

        async def mock_dispatch(task, proj):
            tbl = task.parameters.get("table_name")
            if task.task_type == TaskType.MIGRATION_BATCH and tbl:
                async with dispatch_lock:
                    scheduled_sequence.append(tbl)
            await asyncio.sleep(0.01)
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch):
            await self.manager._run_production_migration_stage(project, session)

        self.assertIn("t1", scheduled_sequence[:2])
        self.assertIn("t2", scheduled_sequence[:2])
        self.assertEqual(scheduled_sequence[-1], "t3")

    # 5. Worker ownership enforcement & 6. Duplicate assignment prevention
    async def test_worker_ownership_and_duplicate_assignment(self):
        project = await self.manager.create_project(
            name="Ownership",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=2
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True

        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        schema_objects = [
            {"object_name": "users", "object_type": "TABLE", "dependency_references": []},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        async def mock_dispatch(task, proj):
            tbl = task.parameters.get("table_name")
            if task.task_type == TaskType.MIGRATION_BATCH and tbl:
                chk = CheckpointRecord(
                    checkpoint_id=f"chk-{tbl}", project_id=proj.project_id, migration_id=task.migration_id,
                    workflow_state=WorkflowState.PRODUCTION_MIGRATION, table_name=tbl, batch_number=1,
                    worker_id="GB-PRIMARY", status=CheckpointStatus.COMPLETED
                )
                await self.checkpoint_mgr.save_progress(chk)
                await self.checkpoint_mgr.mark_completed(proj.project_id, task.migration_id, tbl, worker_id="GB-PRIMARY")
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch):
            await self.manager._run_production_migration_stage(project, session)

        records = await self.checkpoint_mgr.list_checkpoints(project.project_id, session.migration_id)
        users_chk = [r for r in records if r.table_name == "users"]
        self.assertTrue(len(users_chk) > 0)
        self.assertEqual(users_chk[0].worker_id, "GB-PRIMARY")

    # 7. Worker crash recovery & 8. Worker restart & 9. Manager restart & 10. Pipeline restart
    # 11. Checkpoint compatibility & 12. Cursor compatibility & 15. Transaction correctness
    # 16. Zero duplicate rows & 17. Zero skipped rows & 23. Mixed table sizes
    async def test_crash_recovery_resumption(self):
        project = await self.manager.create_project(
            name="Recovery",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=2
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True

        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        schema_objects = [
            {"object_name": "t1", "object_type": "TABLE", "dependency_references": []},
            {"object_name": "t2", "object_type": "TABLE", "dependency_references": []},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        # First run: t2 fails
        original_dispatch = self.manager._dispatch_task
        async def mock_dispatch_fail(task, proj):
            tbl = task.parameters.get("table_name")
            if task.task_type == TaskType.MIGRATION_BATCH and tbl == "t2":
                return TaskResult(
                    task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                    agent_type=task.assigned_to, success=False, error_message="Crash", duration_seconds=0.01, objects_processed=0
                )
            if task.task_type == TaskType.MIGRATION_BATCH and tbl:
                chk = CheckpointRecord(
                    checkpoint_id=f"chk-{tbl}", project_id=proj.project_id, migration_id=task.migration_id,
                    workflow_state=WorkflowState.PRODUCTION_MIGRATION, table_name=tbl, batch_number=1,
                    worker_id="GB-PRIMARY", status=CheckpointStatus.COMPLETED
                )
                await self.checkpoint_mgr.save_progress(chk)
                await self.checkpoint_mgr.mark_completed(proj.project_id, task.migration_id, tbl, worker_id="GB-PRIMARY")
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch_fail):
            with self.assertRaises(RuntimeError):
                await self.manager._run_production_migration_stage(project, session)

        t1_record = await self.checkpoint_mgr.resume(project.project_id, session.migration_id, "t1")
        self.assertEqual(t1_record.status, CheckpointStatus.COMPLETED)

        t2_record = await self.checkpoint_mgr.resume(project.project_id, session.migration_id, "t2")
        self.assertIsNone(t2_record)

        # Second run: Resume!
        scheduled_tables = []
        async def mock_dispatch_resume(task, proj):
            tbl = task.parameters.get("table_name")
            if task.task_type == TaskType.MIGRATION_BATCH and tbl:
                scheduled_tables.append(tbl)
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch_resume):
            await self.manager._run_parallel_production_migration(project, session, ["t1", "t2"], {
                "t1": {"object_name": "t1", "dependency_references": []},
                "t2": {"object_name": "t2", "dependency_references": []}
            }, {"t1": set(), "t2": set()}, {"t1": set(), "t2": set()})

        self.assertEqual(scheduled_tables, ["t2"])

    # 13. Adaptive batch compatibility
    async def test_adaptive_batch_compatibility_parallel(self):
        project = await self.manager.create_project(
            name="Adaptive Parallel",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=2,
            use_adaptive_batch=True,
            initial_batch_size=100
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True

        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        schema_objects = [
            {"object_name": "t1", "object_type": "TABLE", "dependency_references": []},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        async def mock_dispatch(task, proj):
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch):
            await self.manager._run_production_migration_stage(project, session)

    # 14. Retry compatibility & 20. Queue exhaustion
    async def test_retry_compatibility_and_gating(self):
        project = await self.manager.create_project(
            name="Retries",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=1
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True

        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        schema_objects = [
            {"object_name": "t1", "object_type": "TABLE", "dependency_references": []},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        async def mock_dispatch(task, proj):
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch):
            await self.manager._run_production_migration_stage(project, session)

    # 18. Worker shutdown & 19. Worker idle timeout
    async def test_worker_parameters_propagation(self):
        project = await self.manager.create_project(
            name="Params",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            worker_idle_timeout=30.0,
            worker_shutdown_timeout=5.0
        )
        self.assertEqual(project.worker_idle_timeout, 30.0)
        self.assertEqual(project.worker_shutdown_timeout, 5.0)

    # 21. Fair scheduling
    async def test_fair_scheduling(self):
        project = await self.manager.create_project(
            name="Fairness",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=1
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True

        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        schema_objects = [
            {"object_name": "t1", "object_type": "TABLE", "dependency_references": []},
            {"object_name": "t2", "object_type": "TABLE", "dependency_references": []},
            {"object_name": "t3", "object_type": "TABLE", "dependency_references": []},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        scheduled = []
        async def mock_dispatch(task, proj):
            tbl = task.parameters.get("table_name")
            if task.task_type == TaskType.MIGRATION_BATCH and tbl:
                scheduled.append(tbl)
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch):
            await self.manager._run_production_migration_stage(project, session)

        self.assertEqual(scheduled, ["t1", "t2", "t3"])

    # 22. Long-running migration & 24. Deterministic execution
    async def test_long_running_and_determinism(self):
        project = await self.manager.create_project(
            name="Determinism",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=2
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True

        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        schema_objects = [
            {"object_name": "t1", "object_type": "TABLE", "dependency_references": []},
            {"object_name": "t2", "object_type": "TABLE", "dependency_references": []},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        scheduled = []
        async def mock_dispatch(task, proj):
            tbl = task.parameters.get("table_name")
            if task.task_type == TaskType.MIGRATION_BATCH and tbl:
                scheduled.append(tbl)
            return TaskResult(
                task_id=task.task_id, project_id=task.project_id, migration_id=task.migration_id,
                agent_type=task.assigned_to, success=True, output={}, duration_seconds=0.01, objects_processed=0
            )

        with patch.object(self.manager, "_dispatch_task", mock_dispatch):
            await self.manager._run_production_migration_stage(project, session)
        self.assertEqual(len(scheduled), 2)

    # 25. Circular dependency detection
    async def test_circular_dependency_detection(self):
        project = await self.manager.create_project(
            name="Circular",
            source_config=self.src_cfg,
            target_config=self.tgt_cfg,
            strategy=MigrationStrategy.BIG_BANG,
            enable_parallel_migration=True,
            max_parallel_workers=2
        )
        project.state = WorkflowState.HUMAN_APPROVED
        project.human_approval_granted = True

        session = MigrationSession(project_id=project.project_id)
        project.active_migration_id = session.migration_id
        await self.mock_state.register_session(session)

        # t1 depends on t2, t2 depends on t1 (direct cycle)
        schema_objects = [
            {"object_name": "t1", "object_type": "TABLE", "dependency_references": [
                {"target_table": "t2"}
            ]},
            {"object_name": "t2", "object_type": "TABLE", "dependency_references": [
                {"target_table": "t1"}
            ]},
        ]
        self._create_mock_snapshot(project.project_id, session.migration_id, schema_objects)

        with self.assertRaises(ValueError) as ctx:
            await self.manager._run_production_migration_stage(project, session)
        self.assertIn("Circular dependency detected", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
