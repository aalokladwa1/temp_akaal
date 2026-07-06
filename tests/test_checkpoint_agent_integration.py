"""
Akaal — CheckpointAgent Integration Test Suite
================================================
Validates checkpoint creation/restoration message dispatch, corruption handling, 
and task result generation using mocked dependencies.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

from akaal.agents.checkpoint.checkpoint_agent import CheckpointAgent
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.models.enums import AgentStatus, AgentType, TaskType, WorkflowState
from akaal.core.models.message import Message, MessageType
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus


class TestCheckpointAgentIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test cases verifying CheckpointAgent behavior using mock components."""

    async def asyncSetUp(self) -> None:
        self.mock_state = MagicMock(spec=GlobalState)
        self.mock_bus = MagicMock(spec=MessageBus)
        
        # AsyncMock for checkpoint manager calls
        self.mock_manager = MagicMock(spec=CheckpointManager)
        self.mock_manager.save_progress = AsyncMock()
        self.mock_manager.load_progress = AsyncMock()
        self.mock_manager.storage = MagicMock()
        self.mock_manager.storage.__class__.__name__ = "MockStorage"
        
        # Mock register/update calls in GlobalState
        self.mock_state.register_agent = AsyncMock()
        self.mock_state.update_agent_status = AsyncMock()
        self.mock_state.register_checkpoint = AsyncMock()
        
        # Mock message bus publish
        self.published_messages = []
        async def mock_publish(msg):
            self.published_messages.append(msg)
            return True
        self.mock_bus.publish = AsyncMock(side_effect=mock_publish)

        # Instantiate agent under test
        self.agent = CheckpointAgent(
            global_state=self.mock_state,
            message_bus=self.mock_bus,
            checkpoint_manager=self.mock_manager,
            agent_id="CHECKPOINT-INTEGRATION-PRIMARY",
            is_backup=False
        )
        await self.agent.start()

    async def asyncTearDown(self) -> None:
        await self.agent.stop()

    async def test_checkpoint_create_dispatch(self) -> None:
        """Verify successful CHECKPOINT_CREATE dispatch registers the entry and publishes a task result."""
        self.mock_manager.save_progress.return_value = True

        task_msg = Message(
            sender=AgentType.MANAGER,
            receiver=AgentType.CHECKPOINT_ENGINE,
            message_type=MessageType.TASK_ASSIGN,
            payload={
                "task_id": "task-create-111",
                "task_type": TaskType.CHECKPOINT_CREATE.value,
                "parameters": {
                    "checkpoint_id": "cp-create-111",
                    "description": "Post-discovery step",
                    "project_state": {"state": WorkflowState.DISCOVERY_STARTED.value},
                    "global_state_snapshot": {"total_projects": 1}
                }
            },
            project_id="proj-123",
            migration_id="mig-456"
        )

        # Directly invoke handle message (simulating message bus dispatch)
        await self.agent._handle_message(task_msg)
        
        # Give asyncio tasks a small tick to execute
        await asyncio.sleep(0.05)

        # 1. Assert CheckpointManager.save_progress was called
        self.mock_manager.save_progress.assert_called_once()
        saved_record = self.mock_manager.save_progress.call_args[0][0]
        self.assertIsInstance(saved_record, CheckpointRecord)
        self.assertEqual(saved_record.checkpoint_id, "cp-create-111")
        self.assertEqual(saved_record.workflow_state, WorkflowState.DISCOVERY_STARTED)
        self.assertEqual(saved_record.adapter_state.get("global_state_snapshot"), {"total_projects": 1})

        # 2. Assert GlobalState.register_checkpoint was called
        self.mock_state.register_checkpoint.assert_called_once()

        # 3. Assert TASK_RESULT was sent
        self.assertEqual(len(self.published_messages), 1)
        result_msg = self.published_messages[0]
        self.assertEqual(result_msg.message_type, MessageType.TASK_RESULT)
        self.assertEqual(result_msg.payload.get("task_id"), "task-create-111")
        self.assertEqual(result_msg.payload.get("checkpoint_id"), "cp-create-111")
        self.assertIn("cp-create-111", result_msg.payload.get("result_ref"))

    async def test_checkpoint_restore_dispatch(self) -> None:
        """Verify successful CHECKPOINT_RESTORE restores project fields and publishes a task result."""
        # Setup mock loaded record
        mock_record = CheckpointRecord(
            checkpoint_id="cp-restore-222",
            project_id="proj-123",
            migration_id="mig-456",
            workflow_state=WorkflowState.PRODUCTION_MIGRATION,
            table_name="accounts",
            batch_number=5,
            adapter_state={
                "project_state": {
                    "state": WorkflowState.PRODUCTION_MIGRATION.value,
                    "human_approval_granted": True,
                    "approved_by": "admin@akaal.io",
                    "total_objects_migrated": 100
                }
            }
        )
        self.mock_manager.load_progress.return_value = mock_record

        # Setup mock project inside GlobalState
        mock_project = MagicMock()
        mock_project.state = WorkflowState.IDLE
        mock_project.human_approval_granted = False
        self.mock_state.get_project = AsyncMock(return_value=mock_project)

        task_msg = Message(
            sender=AgentType.MANAGER,
            receiver=AgentType.CHECKPOINT_ENGINE,
            message_type=MessageType.TASK_ASSIGN,
            payload={
                "task_id": "task-restore-222",
                "task_type": TaskType.CHECKPOINT_RESTORE.value,
                "parameters": {
                    "checkpoint_id": "cp-restore-222"
                }
            },
            project_id="proj-123",
            migration_id="mig-456"
        )

        await self.agent._handle_message(task_msg)
        await asyncio.sleep(0.05)

        # 1. Verify manager.load_progress called
        self.mock_manager.load_progress.assert_called_once_with("cp-restore-222")

        # 2. Verify project properties restored
        self.assertEqual(mock_project.state, WorkflowState.PRODUCTION_MIGRATION)
        self.assertTrue(mock_project.human_approval_granted)
        self.assertEqual(mock_project.approved_by, "admin@akaal.io")
        self.assertEqual(mock_project.total_objects_migrated, 100)

        # 3. Verify TASK_RESULT published
        self.assertEqual(len(self.published_messages), 1)
        result_msg = self.published_messages[0]
        self.assertEqual(result_msg.message_type, MessageType.TASK_RESULT)
        self.assertEqual(result_msg.payload.get("task_id"), "task-restore-222")
        self.assertEqual(result_msg.payload.get("checkpoint_id"), "cp-restore-222")

    async def test_invalid_checkpoint(self) -> None:
        """Verify load_progress returning None publishes TASK_FAILED."""
        self.mock_manager.load_progress.return_value = None

        task_msg = Message(
            sender=AgentType.MANAGER,
            receiver=AgentType.CHECKPOINT_ENGINE,
            message_type=MessageType.TASK_ASSIGN,
            payload={
                "task_id": "task-restore-333",
                "task_type": TaskType.CHECKPOINT_RESTORE.value,
                "parameters": {
                    "checkpoint_id": "cp-invalid"
                }
            },
            project_id="proj-123",
            migration_id="mig-456"
        )

        await self.agent._handle_message(task_msg)
        await asyncio.sleep(0.05)

        # Assert TASK_FAILED sent
        self.assertEqual(len(self.published_messages), 1)
        fail_msg = self.published_messages[0]
        self.assertEqual(fail_msg.message_type, MessageType.TASK_FAILED)
        self.assertEqual(fail_msg.payload.get("task_id"), "task-restore-333")
        self.assertIn("not found", fail_msg.payload.get("error").lower())

    async def test_corrupted_checkpoint(self) -> None:
        """Verify load_progress raising ValueError (integrity mismatch) publishes TASK_FAILED."""
        self.mock_manager.load_progress.side_effect = ValueError("CHECKPOINT CORRUPTION: Checksum mismatch")

        task_msg = Message(
            sender=AgentType.MANAGER,
            receiver=AgentType.CHECKPOINT_ENGINE,
            message_type=MessageType.TASK_ASSIGN,
            payload={
                "task_id": "task-restore-444",
                "task_type": TaskType.CHECKPOINT_RESTORE.value,
                "parameters": {
                    "checkpoint_id": "cp-corrupt"
                }
            },
            project_id="proj-123",
            migration_id="mig-456"
        )

        await self.agent._handle_message(task_msg)
        await asyncio.sleep(0.05)

        # Assert TASK_FAILED containing checkpoint corruption details
        self.assertEqual(len(self.published_messages), 1)
        fail_msg = self.published_messages[0]
        self.assertEqual(fail_msg.message_type, MessageType.TASK_FAILED)
        self.assertEqual(fail_msg.payload.get("task_id"), "task-restore-444")
        self.assertIn("checkpoint corruption", fail_msg.payload.get("error").lower())

    async def test_storage_exception_propagation(self) -> None:
        """Verify write exception propagation publishes TASK_FAILED."""
        self.mock_manager.save_progress.side_effect = RuntimeError("Disk quota exceeded")

        task_msg = Message(
            sender=AgentType.MANAGER,
            receiver=AgentType.CHECKPOINT_ENGINE,
            message_type=MessageType.TASK_ASSIGN,
            payload={
                "task_id": "task-create-555",
                "task_type": TaskType.CHECKPOINT_CREATE.value,
                "parameters": {
                    "checkpoint_id": "cp-err",
                    "project_state": {"state": WorkflowState.DISCOVERY_STARTED.value}
                }
            },
            project_id="proj-123",
            migration_id="mig-456"
        )

        await self.agent._handle_message(task_msg)
        await asyncio.sleep(0.05)

        # Assert TASK_FAILED published containing Disk quota exceeded details
        self.assertEqual(len(self.published_messages), 1)
        fail_msg = self.published_messages[0]
        self.assertEqual(fail_msg.message_type, MessageType.TASK_FAILED)
        self.assertEqual(fail_msg.payload.get("task_id"), "task-create-555")
        self.assertIn("disk quota exceeded", fail_msg.payload.get("error").lower())
