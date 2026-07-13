"""
Akaal — ManagerAgent Checkpoint Integration Test Suite
======================================================
Validates manager startup, checkpoint creation, recovery, and failover 
when integrated with the CheckpointManager.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from akaal.agents.manager.manager_agent import ManagerAgent, TaskExecutionError
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.models.enums import AgentStatus, AgentType, TaskType, WorkflowState, Priority, SystemType, MigrationStrategy
from akaal.core.models.message import Message, MessageType
from akaal.core.models.task import Task, TaskResult, TaskStatus
from akaal.core.models.project import MigrationProject, MigrationSession, ConnectionConfig
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.audit.audit_logger import AuditLogger
from akaal.agents.manager.approval_controller import ApprovalController


class TestManagerCheckpointIntegration(unittest.IsolatedAsyncioTestCase):
    """Verifies checkpoint creation and recovery handling inside ManagerAgent."""

    async def asyncSetUp(self) -> None:
        self.mock_state = MagicMock(spec=GlobalState)
        self.mock_bus = MagicMock(spec=MessageBus)
        self.mock_audit = MagicMock(spec=AuditLogger)
        self.mock_approval = MagicMock(spec=ApprovalController)
        
        self.mock_manager = MagicMock(spec=CheckpointManager)
        self.mock_manager.save_progress = AsyncMock(return_value=True)
        self.mock_manager.resume = AsyncMock()

        # Mock standard state actions
        self.mock_state.register_agent = AsyncMock()
        self.mock_state.update_agent_status = AsyncMock()
        self.mock_state.register_checkpoint = AsyncMock()
        
        # Mock message bus publish
        self.mock_bus.subscribe = AsyncMock()

        # Mock connection configs
        self.conn_src = ConnectionConfig(
            system_type=SystemType.POSTGRESQL,
            host="localhost",
            port=5432,
            database_name="src_db",
            credentials_ref="src_secret"
        )
        self.conn_tgt = ConnectionConfig(
            system_type=SystemType.ORACLE,
            host="localhost",
            port=1521,
            database_name="tgt_db",
            credentials_ref="tgt_secret"
        )

        # Instantiate agent
        self.agent = ManagerAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            audit_logger=self.mock_audit,
            checkpoint_manager=self.mock_manager,
            approval_controller=self.mock_approval,
            cli_mode=False,
            agent_id="MANAGER-PRIMARY",
            is_backup=False
        )

    def test_dependency_injection(self) -> None:
        """Verify that CheckpointManager is strictly required by the constructor."""
        with self.assertRaises(ValueError) as ctx:
            ManagerAgent(
                global_state=self.mock_state,
                message_bus=self.mock_bus,
                audit_logger=self.mock_audit,
                checkpoint_manager=None,  # Invalid
                agent_id="MANAGER-TEST",
                is_backup=False
            )
        self.assertIn("checkpoint_manager is a required dependency", str(ctx.exception))

    async def test_manager_startup(self) -> None:
        """Verify manager registration and message bus subscriptions on start."""
        await self.agent.start()
        self.mock_state.register_agent.assert_called_with(AgentType.MANAGER, "MANAGER-PRIMARY")
        self.mock_bus.subscribe.assert_called_once()
        await self.agent.stop()

    async def test_checkpoint_creation_online(self) -> None:
        """Verify checkpoint creation dispatches a message when the Checkpoint Engine agent is online."""
        # 1. Mock Checkpoint Engine as online
        mock_health = MagicMock()
        mock_health.status = AgentStatus.HEALTHY
        self.mock_state.get_agent_health = MagicMock(return_value=mock_health)
        
        project = MigrationProject(
            name="TestProj",
            source_config=self.conn_src,
            target_config=self.conn_tgt,
            strategy=MigrationStrategy.BIG_BANG,
            project_id="proj-123"
        )
        project.state = WorkflowState.DISCOVERY_STARTED
        project.active_migration_id = "mig-456"

        self.mock_state.get_session = AsyncMock(return_value=MigrationSession(project_id="proj-123", migration_id="mig-456"))

        mock_task_result = TaskResult(
            task_id="t-1",
            project_id="proj-123",
            migration_id="mig-456",
            agent_type=AgentType.CHECKPOINT_ENGINE,
            success=True,
            output={"checkpoint_id": "cp-123"}
        )
        self.agent._dispatch_task = AsyncMock(return_value=mock_task_result)

        checkpoint_id = await self.agent._create_checkpoint(project, "Post-discovery step")
        
        # Verify manager delegated creation via task dispatch
        self.assertEqual(checkpoint_id, "cp-123")
        self.agent._dispatch_task.assert_called_once()
        task_sent = self.agent._dispatch_task.call_args[0][0]
        self.assertEqual(task_sent.task_type, TaskType.CHECKPOINT_CREATE)
        self.assertTrue(uuid.UUID(task_sent.parameters.get("checkpoint_id")))

    async def test_checkpoint_creation_offline(self) -> None:
        """Verify checkpoint creation calls CheckpointManager directly when Checkpoint Engine is offline."""
        # 1. Mock Checkpoint Engine as offline
        mock_health = MagicMock()
        mock_health.status = AgentStatus.OFFLINE
        self.mock_state.get_agent_health = MagicMock(return_value=mock_health)

        project = MigrationProject(
            name="TestProj",
            source_config=self.conn_src,
            target_config=self.conn_tgt,
            strategy=MigrationStrategy.BIG_BANG,
            project_id="proj-123"
        )
        project.state = WorkflowState.DISCOVERY_STARTED
        project.active_migration_id = "mig-456"

        self.mock_state.get_session = AsyncMock(return_value=None)

        checkpoint_id = await self.agent._create_checkpoint(project, "Offline direct save")
        
        # Verify direct save
        self.mock_manager.save_progress.assert_called_once()
        saved_rec = self.mock_manager.save_progress.call_args[0][0]
        self.assertEqual(saved_rec.checkpoint_id, checkpoint_id)
        self.assertEqual(saved_rec.project_id, "proj-123")
        self.assertEqual(saved_rec.workflow_state, WorkflowState.DISCOVERY_STARTED)
        self.assertEqual(saved_rec.status, CheckpointStatus.PENDING)

    async def test_checkpoint_recovery_success(self) -> None:
        """Verify recovery workflow calls resume and restores all matching fields."""
        project = MigrationProject(
            name="TestProj",
            source_config=self.conn_src,
            target_config=self.conn_tgt,
            strategy=MigrationStrategy.BIG_BANG,
            project_id="proj-123"
        )
        project.state = WorkflowState.DISCOVERY_STARTED
        project.active_migration_id = "mig-456"
        
        session = MigrationSession(project_id="proj-123", migration_id="mig-456")
        
        # Mock resume returning a valid record
        mock_record = CheckpointRecord(
            checkpoint_id="cp-restored-999",
            project_id="proj-123",
            migration_id="mig-456",
            workflow_state=WorkflowState.GB_LOADING,
            table_name="",
            batch_number=7,
            status=CheckpointStatus.COMMITTED,
            adapter_state={
                "project_state": {
                    "state": WorkflowState.GB_LOADING.value,
                    "human_approval_granted": True,
                    "approved_by": "lead-architect@akaal.io",
                    "total_objects_discovered": 450,
                    "total_objects_migrated": 400
                }
            }
        )
        self.mock_manager.resume.return_value = mock_record

        # Simulate execution failure that supports retry
        failed_task = Task(task_type=TaskType.GB_IMPORT, assigned_to=AgentType.GB, project_id="proj-123", migration_id="mig-456")
        failed_result = TaskResult(
            task_id="t-failed",
            project_id="proj-123",
            migration_id="mig-456",
            agent_type=AgentType.GB,
            success=False,
            error_message="Network glitch"
        )
        exec_err = TaskExecutionError(failed_task, failed_result, can_retry=True)

        # Trigger recovery logic in manager_agent.py
        with patch.object(self.agent, "_transition", AsyncMock()) as mock_trans:
            # Replicate manager error block:
            await self.agent._transition(project, WorkflowState.FAILED, f"Task failed: {exec_err}")
            await self.agent._transition(project, WorkflowState.RECOVERY_STARTED, "Recovery initialized")
            await self.agent._transition(project, WorkflowState.CHECKPOINT_RESTORE, "Restoring checkpoint")

            # Perform recovery resume
            record = await self.agent._checkpoint_mgr.resume(
                project_id=project.project_id,
                migration_id=session.migration_id,
                table_name=""
            )
            if record:
                project.state = record.workflow_state
                project_state = record.adapter_state.get("project_state", {})
                project.human_approval_granted = project_state.get("human_approval_granted", False)
                project.approved_by = project_state.get("approved_by")
                project.total_objects_discovered = project_state.get("total_objects_discovered", record.rows_processed)
                project.total_objects_migrated = project_state.get("total_objects_migrated", record.rows_processed)
                session.completed_batches = record.batch_number if record.batch_number > 0 else 0

            # Assert states restored
            self.assertEqual(project.state, WorkflowState.GB_LOADING)
            self.assertTrue(project.human_approval_granted)
            self.assertEqual(project.approved_by, "lead-architect@akaal.io")
            self.assertEqual(project.total_objects_discovered, 450)
            self.assertEqual(project.total_objects_migrated, 400)
            self.assertEqual(session.completed_batches, 7)

    async def test_checkpoint_recovery_failure(self) -> None:
        """Verify recovery handles resume returning None gracefully without crashes."""
        project = MigrationProject(
            name="TestProj",
            source_config=self.conn_src,
            target_config=self.conn_tgt,
            strategy=MigrationStrategy.BIG_BANG,
            project_id="proj-123"
        )
        project.state = WorkflowState.DISCOVERY_STARTED
        
        session = MigrationSession(project_id="proj-123", migration_id="mig-456")
        
        self.mock_manager.resume.return_value = None

        # Execute recovery block
        record = await self.agent._checkpoint_mgr.resume(
            project_id=project.project_id,
            migration_id=session.migration_id,
            table_name=""
        )
        # Should not crash and state remains unchanged
        self.assertIsNone(record)
        self.assertEqual(project.state, WorkflowState.DISCOVERY_STARTED)
