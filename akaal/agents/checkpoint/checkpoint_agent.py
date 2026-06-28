"""
NexusForge — Checkpoint Engine Agent
====================================
Handles workflow state serialization, persistence, integrity checks, and restorations.
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Set

from akaal.core.models.enums import AgentStatus, AgentType, TaskType, WorkflowState
from akaal.core.models.message import Message, MessageType
from akaal.core.state.global_state import CheckpointEntry, GlobalState
from akaal.core.message_bus.bus import MessageBus

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
        workspace_dir: str = "workspace",
        agent_id: str = "CHECKPOINT-001",
        is_backup: bool = False,
    ) -> None:
        self._state = global_state
        self._bus = message_bus
        self._workspace_dir = workspace_dir
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
        - Capture serialized workflow state and snapshot
        - Compute SHA-256 state hash
        - Persist to disk
        - Register CheckpointEntry in global state
        """
        checkpoint_id = parameters.get("checkpoint_id")
        description = parameters.get("description", "Workflow checkpoint")
        project_state = parameters.get("project_state", {})
        global_state_snapshot = parameters.get("global_state_snapshot", {})

        if not checkpoint_id:
            raise ValueError("checkpoint_id is required in parameters.")

        payload = {
            "project_state": project_state,
            "global_state_snapshot": global_state_snapshot
        }

        # Calculate checksum of the payload to guarantee integrity
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(payload_bytes).hexdigest()

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "project_id": project_id,
            "migration_id": migration_id,
            "workflow_state": project_state.get("state"),
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "checksum": checksum,
            "payload": payload
        }

        # Write checkpoint file to disk
        project_dir = os.path.join(self._workspace_dir, "projects", project_id)
        os.makedirs(project_dir, exist_ok=True)
        filepath = os.path.join(project_dir, f"checkpoint_{checkpoint_id}.json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)

        # Register in global state
        entry = CheckpointEntry(
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            migration_id=migration_id,
            workflow_state=WorkflowState(project_state.get("state")),
            description=description
        )
        await self._state.register_checkpoint(entry)

        logger.info("[CheckpointAgent] Saved checkpoint file to %s and registered entry", filepath)
        return {
            "checkpoint_id": checkpoint_id,
            "result_ref": filepath
        }

    async def _handle_checkpoint_restore(self, project_id: str, migration_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle TaskType.CHECKPOINT_RESTORE:
        - Read snapshot file from disk
        - Verify checksum integrity
        - Restore in-memory state fields
        """
        checkpoint_id = parameters.get("checkpoint_id")
        if not checkpoint_id:
            raise ValueError("checkpoint_id is required in parameters.")

        # Read checkpoint file
        filepath = os.path.join(self._workspace_dir, "projects", project_id, f"checkpoint_{checkpoint_id}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Checkpoint file not found at {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            checkpoint_data = json.load(f)

        # Verify integrity using checksum
        payload = checkpoint_data.get("payload", {})
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        computed_checksum = hashlib.sha256(payload_bytes).hexdigest()

        if computed_checksum != checkpoint_data.get("checksum"):
            raise ValueError(f"CHECKPOINT CORRUPTION: Checksum verification failed for checkpoint {checkpoint_id}.")

        # Restore project state in memory
        project = await self._state.get_project(project_id)
        if project:
            saved_project = payload.get("project_state", {})
            project.state = WorkflowState(saved_project.get("state", project.state.value))
            project.human_approval_granted = saved_project.get("human_approval_granted", False)
            project.approved_by = saved_project.get("approved_by")
            project.approved_at = saved_project.get("approved_at")
            project.total_objects_discovered = saved_project.get("total_objects_discovered", 0)
            project.total_objects_migrated = saved_project.get("total_objects_migrated", 0)
            project.validation_pass_count = saved_project.get("validation_pass_count", 0)
            project.validation_fail_count = saved_project.get("validation_fail_count", 0)

            logger.info("[CheckpointAgent] Restored global project state for %s to state=%s", project_id, project.state.value)

        return {
            "checkpoint_id": checkpoint_id,
            "result_ref": filepath
        }
