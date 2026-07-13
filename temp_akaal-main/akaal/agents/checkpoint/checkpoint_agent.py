"""
NexusForge — Checkpoint Engine Agent
====================================
Handles workflow state serialization, persistence, integrity checks, and restorations.
Delegates all persistence operations to CheckpointManager.
"""

import asyncio
import logging
from typing import Any, Dict, Set

from akaal.core.models.enums import AgentStatus, AgentType, TaskType, WorkflowState
from akaal.core.models.message import Message, MessageType
from akaal.core.state.global_state import CheckpointEntry, GlobalState
from akaal.core.message_bus.bus import MessageBus
from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager

logger = logging.getLogger("nexusforge.checkpoint")


class CheckpointAgent:
    """
    The Checkpoint Engine Agent acts as the state preservation and recovery backbone.
    """

    AGENT_ID: str = "CHECKPOINT-001"

    def __init__(
        self,
        global_state: GlobalState,
        message_bus: MessageBus,
        checkpoint_manager: CheckpointManager,
        agent_id: str = "CHECKPOINT-001",
        is_backup: bool = False,
    ) -> None:
        """
        Initialize the CheckpointAgent.
        Args:
            global_state: Authoritative GlobalState instance.
            message_bus: System MessageBus instance.
            checkpoint_manager: CheckpointManager instance for persistence delegation (Required).
            agent_id: String identifier for active/standby pairs.
            is_backup: Flag indicating active/standby mode.
        """
        if checkpoint_manager is None:
            raise ValueError("checkpoint_manager is a required dependency and cannot be None.")

        self._state = global_state
        self._bus = message_bus
        self._manager = checkpoint_manager
        self.agent_id = agent_id
        self._is_backup = is_backup
        self._running = False
        self._active_tasks: Set[str] = set()

        logger.info("[CheckpointAgent] Constructed. ID=%s (Backup=%s)", self.agent_id, self._is_backup)

    async def start(self) -> None:
        """Register the agent with global state and subscribe to the message bus."""
        self._running = True
        status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
        await self._state.register_agent(AgentType.CHECKPOINT_ENGINE, self.agent_id)
        await self._state.update_agent_status(AgentType.CHECKPOINT_ENGINE, status, self.agent_id)

        # Subscribe to message bus for CHECKPOINT_ENGINE queue
        await self._bus.subscribe(AgentType.CHECKPOINT_ENGINE, self._handle_message)
        logger.info("[CheckpointAgent] Started and registered.")

    async def stop(self) -> None:
        """Graceful shutdown of the agent."""
        self._running = False
        await self._state.update_agent_status(AgentType.CHECKPOINT_ENGINE, AgentStatus.OFFLINE, self.agent_id)
        logger.info("[CheckpointAgent] Stopped.")

    async def _handle_message(self, message: Message) -> None:
        """Handle incoming messages from message bus."""
        if not self._running:
            return

        if not message.verify_integrity():
            logger.error("[CheckpointAgent] Message integrity check failed. Discarding message %s", message.message_id)
            return

        # Handle active-standby control messages
        payload = message.payload or {}
        target_id = payload.get("target_agent_id")

        if message.message_type == "PROMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = False
                await self._state.promote_agent_instance(AgentType.CHECKPOINT_ENGINE, self.agent_id)
            return

        if message.message_type == "DEMOTION":
            if target_id == self.agent_id or not target_id:
                self._is_backup = True
                await self._state.update_agent_status(AgentType.CHECKPOINT_ENGINE, AgentStatus.STANDBY, self.agent_id)
            return

        if message.message_type == "REPAIR":
            if target_id == self.agent_id or not target_id:
                # Reset error count
                health = self._state.get_agent_instance_health(self.agent_id)
                if health:
                    health.error_count = 0
                status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
                await self._state.update_agent_status(AgentType.CHECKPOINT_ENGINE, status, self.agent_id)
                logger.critical("[CheckpointAgent %s] Repaired. Status restored to %s.", self.agent_id, status.value)
            return

        # Ignore tasks if in standby
        if self._is_backup:
            logger.debug("[CheckpointAgent %s] STANDBY MODE: Ignoring message of type %s.", self.agent_id, message.message_type)
            return

        if message.message_type == MessageType.TASK_ASSIGN:
            task_id = message.payload.get("task_id")
            project_id = message.project_id or ""
            migration_id = message.migration_id or ""
            if task_id:
                asyncio.create_task(self._execute_task(message.payload, project_id, migration_id))

    async def _execute_task(self, task_dict: Dict[str, Any], project_id: str, migration_id: str) -> None:
        """Execute the assigned task."""
        task_id = task_dict["task_id"]
        task_type_str = task_dict["task_type"]
        parameters = task_dict.get("parameters", {})

        if task_id in self._active_tasks:
            logger.warning("[CheckpointAgent] Task %s is already running.", task_id)
            return

        self._active_tasks.add(task_id)
        await self._state.update_agent_status(AgentType.CHECKPOINT_ENGINE, AgentStatus.BUSY, self.agent_id)

        logger.info("[CheckpointAgent] Started task %s (Type=%s)", task_id[:8], task_type_str)

        try:
            if task_type_str == TaskType.CHECKPOINT_CREATE.value:
                res_payload = await self._handle_checkpoint_create(project_id, migration_id, parameters)
            elif task_type_str == TaskType.CHECKPOINT_RESTORE.value:
                res_payload = await self._handle_checkpoint_restore(project_id, migration_id, parameters)
            else:
                raise NotImplementedError(f"Task type {task_type_str} is not supported by CheckpointAgent.")

            # Notify Manager of completion
            logger.info("[CheckpointAgent] Task %s completed successfully.", task_id[:8])
            response = Message(
                sender=AgentType.CHECKPOINT_ENGINE,
                receiver=AgentType.MANAGER,
                message_type=MessageType.TASK_RESULT,
                payload={
                    "task_id": task_id,
                    **res_payload
                },
                project_id=project_id,
                migration_id=migration_id,
            )
            await self._bus.publish(response)

        except Exception as exc:
            logger.error("[CheckpointAgent] Task %s failed: %s", task_id[:8], exc, exc_info=True)
            
            # Send failure notification
            fail_msg = Message(
                sender=AgentType.CHECKPOINT_ENGINE,
                receiver=AgentType.MANAGER,
                message_type=MessageType.TASK_FAILED,
                payload={
                    "task_id": task_id,
                    "error": str(exc),
                },
                project_id=project_id,
                migration_id=migration_id,
            )
            await self._bus.publish(fail_msg)

        finally:
            self._active_tasks.discard(task_id)
            status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
            await self._state.update_agent_status(AgentType.CHECKPOINT_ENGINE, status, self.agent_id)

    async def _handle_checkpoint_create(self, project_id: str, migration_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle TaskType.CHECKPOINT_CREATE:
        - Construct CheckpointRecord from parameter mapping.
        - Persist to CheckpointManager.
        - Register in GlobalState.
        """
        checkpoint_id = parameters.get("checkpoint_id")
        description = parameters.get("description", "Workflow checkpoint")
        project_state = parameters.get("project_state", {})
        global_state_snapshot = parameters.get("global_state_snapshot", {})

        if not checkpoint_id:
            raise ValueError("checkpoint_id is required in parameters.")

        state_str = project_state.get("state") or parameters.get("workflow_state")
        workflow_state = WorkflowState(state_str) if state_str else WorkflowState.IDLE

        # Adapter state holds snapshots
        adapter_state = parameters.get("adapter_state", {}).copy()
        adapter_state["project_state"] = project_state
        if global_state_snapshot:
            adapter_state["global_state_snapshot"] = global_state_snapshot

        metrics = parameters.get("metrics", {}).copy()
        metrics["description"] = description

        record = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            migration_id=migration_id,
            workflow_state=workflow_state,
            table_name=parameters.get("table_name", ""),
            batch_number=parameters.get("batch_number", 0),
            worker_id=parameters.get("worker_id", "default"),
            last_processed_primary_key=parameters.get("last_processed_primary_key"),
            rows_processed=parameters.get("rows_processed", 0),
            rows_failed=parameters.get("rows_failed", 0),
            rows_skipped=parameters.get("rows_skipped", 0),
            retry_count=parameters.get("retry_count", 0),
            adapter_state=adapter_state,
            metrics=metrics,
            status=CheckpointStatus.PENDING
        )

        success = await self._manager.save_progress(record)
        if not success:
            raise RuntimeError(f"Failed to persist checkpoint {checkpoint_id} using CheckpointManager.")

        # Register in in-memory global state for active state machine visibility
        entry = CheckpointEntry(
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            migration_id=migration_id,
            workflow_state=workflow_state,
            description=description
        )
        await self._state.register_checkpoint(entry)

        # Establish compatible URI reference path string
        from akaal.core.checkpoint.storage.file_storage import FileCheckpointStorageAdapter
        if isinstance(self._manager.storage, FileCheckpointStorageAdapter):
            result_ref = self._manager.storage._get_file_path(project_id, checkpoint_id)
        else:
            result_ref = f"storage:{self._manager.storage.__class__.__name__}/{checkpoint_id}"

        logger.info("[CheckpointAgent] Saved checkpoint record %s via manager, registered in global state.", checkpoint_id)
        return {
            "checkpoint_id": checkpoint_id,
            "result_ref": result_ref
        }

    async def _handle_checkpoint_restore(self, project_id: str, migration_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle TaskType.CHECKPOINT_RESTORE:
        - Load record using CheckpointManager.
        - Restore in-memory fields in GlobalState project representation.
        """
        checkpoint_id = parameters.get("checkpoint_id")
        if not checkpoint_id:
            raise ValueError("checkpoint_id is required in parameters.")

        record = await self._manager.load_progress(checkpoint_id)
        if not record:
            raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found by manager.")

        # Restore project state in memory
        project = await self._state.get_project(project_id)
        if project:
            project_state = record.adapter_state.get("project_state", {})
            project.state = WorkflowState(project_state.get("state", record.workflow_state.value))
            project.human_approval_granted = project_state.get("human_approval_granted", False)
            project.approved_by = project_state.get("approved_by")
            project.approved_at = project_state.get("approved_at")
            project.total_objects_discovered = project_state.get("total_objects_discovered", record.rows_processed)
            project.total_objects_migrated = project_state.get("total_objects_migrated", record.rows_processed)
            project.validation_pass_count = project_state.get("validation_pass_count", 0)
            project.validation_fail_count = project_state.get("validation_fail_count", 0)

            logger.info("[CheckpointAgent] Restored global project state for %s to state=%s", project_id, project.state.value)

        from akaal.core.checkpoint.storage.file_storage import FileCheckpointStorageAdapter
        if isinstance(self._manager.storage, FileCheckpointStorageAdapter):
            result_ref = self._manager.storage._get_file_path(project_id, checkpoint_id)
        else:
            result_ref = f"storage:{self._manager.storage.__class__.__name__}/{checkpoint_id}"

        return {
            "checkpoint_id": checkpoint_id,
            "result_ref": result_ref
        }
