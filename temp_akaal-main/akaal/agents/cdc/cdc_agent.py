"""
NexusForge — CDC Engine Agent
=============================
The real-time synchronization, change capture, and event propagation engine.
Tracks transaction streams, generates Universal JSON Deltas, manages offset
checkpoints, and supports active-standby failover.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.models.enums import AgentStatus, AgentType, Priority, TaskType
from akaal.core.models.message import Message, MessageType
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus

logger = logging.getLogger("nexusforge.cdc")


class CDCAgent:
    """
    CDCAgent handles real-time change data capture from the source database,
    synchronizing updates as Deltas to GB staging, and managing offset checkpoints.
    Supports Active-Standby hot failover and automatic repairs.
    """

    def __init__(
        self,
        global_state: GlobalState,
        message_bus: MessageBus,
        workspace_dir: str = "workspace",
        agent_id: str = "CDC-ENGINE-PRIMARY",
        is_backup: bool = False,
    ) -> None:
        self._state = global_state
        self._bus = message_bus
        self._workspace_dir = workspace_dir
        self.agent_id = agent_id
        self._is_backup = is_backup
        
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
        self._event_log: List[Dict[str, Any]] = []
        self._replication_offset = 0
        self._tx_counter = 1000

        logger.info(
            "[CDCAgent] Constructed. ID=%s (Backup=%s)",
            self.agent_id, self._is_backup
        )

    async def start(self) -> None:
        """Register the agent and subscribe to the message bus."""
        self._running = True
        status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
        await self._state.register_agent(AgentType.CDC_ENGINE, self.agent_id)
        await self._state.update_agent_status(AgentType.CDC_ENGINE, status, self.agent_id)

        # Register instance in message bus or handle messages
        await self._bus.subscribe(AgentType.CDC_ENGINE, self._handle_message)
        logger.info("[CDCAgent] Started. ID=%s (Status=%s)", self.agent_id, status.value)

    async def stop(self) -> None:
        """Gracefully stop the CDC Agent and its synchronization task."""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None

        await self._state.update_agent_status(AgentType.CDC_ENGINE, AgentStatus.OFFLINE, self.agent_id)
        logger.info("[CDCAgent] Stopped. ID=%s", self.agent_id)

    async def _handle_message(self, message: Message) -> None:
        """Process messages from the bus. Filters standard tasks if in standby."""
        if not self._running:
            return

        if not message.verify_integrity():
            logger.error("[CDCAgent %s] Message integrity check failed.", self.agent_id)
            return

        # 1. Process active-standby control messages (always processed, even in standby)
        payload = message.payload or {}
        target_id = payload.get("target_agent_id")

        if message.message_type == "PROMOTION":
            if target_id == self.agent_id or not target_id:
                await self._promote()
            return

        if message.message_type == "DEMOTION":
            if target_id == self.agent_id or not target_id:
                await self._demote()
            return

        if message.message_type == "REPAIR":
            if target_id == self.agent_id or not target_id:
                await self._repair()
            return

        # 2. Filter standard task assignments if in standby
        if self._is_backup:
            logger.debug(
                "[CDCAgent %s] STANDBY MODE: Ignoring message of type %s.",
                self.agent_id, message.message_type
            )
            return

        # 3. Process active tasks
        if message.message_type == MessageType.TASK_ASSIGN:
            task_id = payload.get("task_id")
            task_type = payload.get("task_type")
            project_id = message.project_id or ""
            migration_id = message.migration_id or ""

            if task_type == TaskType.CDC_SYNC:
                # Start replication sync loop
                if not self._sync_task or self._sync_task.done():
                    self._sync_task = asyncio.create_task(
                        self._replication_sync_loop(task_id, project_id, migration_id)
                    )

    async def _promote(self) -> None:
        """Promote standby instance to active primary."""
        if not self._is_backup:
            return
        self._is_backup = False
        await self._state.promote_agent_instance(AgentType.CDC_ENGINE, self.agent_id)
        logger.critical("[CDCAgent %s] PROMOTED to active Primary CDC Engine.", self.agent_id)

    async def _demote(self) -> None:
        """Demote active instance to standby."""
        if self._is_backup:
            return
        self._is_backup = True
        if self._sync_task:
            self._sync_task.cancel()
            self._sync_task = None
        await self._state.update_agent_status(AgentType.CDC_ENGINE, AgentStatus.STANDBY, self.agent_id)
        logger.warning("[CDCAgent %s] DEMOTED to standby CDC Engine.", self.agent_id)

    async def _repair(self) -> None:
        """Simulate self-healing repair, resetting errors and restoring online loop."""
        logger.info("[CDCAgent %s] Performing internal self-repair...", self.agent_id)
        # Reset error count in state
        health = self._state.get_agent_instance_health(self.agent_id)
        if health:
            health.error_count = 0
        
        # If running, update status to Standby or Healthy depending on config
        status = AgentStatus.STANDBY if self._is_backup else AgentStatus.HEALTHY
        await self._state.update_agent_status(AgentType.CDC_ENGINE, status, self.agent_id)
        logger.critical("[CDCAgent %s] Repair complete. Restored status to %s.", self.agent_id, status.value)

    async def _replication_sync_loop(self, task_id: str, project_id: str, migration_id: str) -> None:
        """Simulates capture and propagation of transactions to GB/Staging."""
        logger.info("[CDCAgent %s] Starting CDC replication sync loop for task %s", self.agent_id, task_id[:8])
        await self._state.update_agent_status(AgentType.CDC_ENGINE, AgentStatus.BUSY, self.agent_id)

        try:
            # Generate mock transactions periodically
            tables = ["users", "orders", "inventory_logs"]
            while self._running and not self._is_backup:
                self._replication_offset += 1
                self._tx_counter += 1
                
                # Alternate INSERT / UPDATE
                change_type = "INSERT" if self._replication_offset % 2 != 0 else "UPDATE"
                table = tables[self._replication_offset % len(tables)]
                
                # Mock Delta Payload
                before = None
                if change_type == "UPDATE":
                    before = {"id": self._replication_offset, "status": "pending"}
                after = {
                    "id": self._replication_offset,
                    "status": "active" if change_type == "UPDATE" else "pending",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

                # Compute checksum of delta
                payload_str = json.dumps({"before": before, "after": after}, sort_keys=True)
                checksum = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

                event = {
                    "sequence_id": self._replication_offset,
                    "tx_id": self._tx_counter,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "change_type": change_type,
                    "table": table,
                    "delta": {
                        "before": before,
                        "after": after
                    },
                    "checksum": checksum
                }
                
                self._event_log.append(event)
                logger.debug(
                    "[CDCAgent %s] Captured change event #%d on %s",
                    self.agent_id, self._replication_offset, table
                )

                # Sync to GB staging layer (represented in memory/logs)
                # Save replication offset in global state
                # (For simplicity we store the offset in the agent health parameters)
                health = self._state.get_agent_instance_health(self.agent_id)
                if health:
                    health.current_task_id = f"offset_{self._replication_offset}"

                # Publish delta packet to GB staging
                delta_msg = Message(
                    sender=AgentType.CDC_ENGINE,
                    receiver=AgentType.GB,
                    message_type="CDC_DELTA_SYNC",
                    payload={"event": event},
                    project_id=project_id,
                    migration_id=migration_id,
                    priority=Priority.P1_MIGRATION
                )
                await self._bus.publish(delta_msg)

                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            logger.info("[CDCAgent %s] Replication loop cancelled.", self.agent_id)
        except Exception as exc:
            logger.error("[CDCAgent %s] Error in replication loop: %s", self.agent_id, exc)
            await self._state.update_agent_status(AgentType.CDC_ENGINE, AgentStatus.FAILED, self.agent_id)
            # Notify manager of CDC failure
            fail_msg = Message(
                sender=AgentType.CDC_ENGINE,
                receiver=AgentType.MANAGER,
                message_type=MessageType.TASK_FAILED,
                payload={"task_id": task_id, "error": str(exc)},
                project_id=project_id,
                migration_id=migration_id,
                priority=Priority.P0_SYSTEM_CRITICAL
            )
            await self._bus.publish(fail_msg)

    def replay_events(self, start_offset: int) -> List[Dict[str, Any]]:
        """Replay historical transaction logs starting from a specific offset."""
        logger.info(
            "[CDCAgent %s] Replaying events from offset %d forward.",
            self.agent_id, start_offset
        )
        return [e for e in self._event_log if e["sequence_id"] >= start_offset]
