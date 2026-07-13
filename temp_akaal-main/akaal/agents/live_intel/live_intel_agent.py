"""
NexusForge — Live Intel Agent
=============================
The real-time diagnostic, prediction, and self-healing intelligence layer.
Observes system telemetry, agent queues, and states to compute health scores,
detect anomalies, recommend repairs, and manage hot-standby failover.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from akaal.core.models.enums import AgentStatus, AgentType, FailureReason, Priority
from akaal.core.models.message import Message, MessageType
from akaal.core.state.global_state import GlobalState
from akaal.core.message_bus.bus import MessageBus

logger = logging.getLogger("nexusforge.live_intel")


class LiveIntelAgent:
    """
    Live Intel Agent continuously monitors system health and generates
    non-executing repair recommendations. Supports hot-standby promotion.
    """

    def __init__(
        self,
        global_state: GlobalState,
        message_bus: MessageBus,
        agent_id: str = "LIVE-INTEL-PRIMARY",
        is_backup: bool = False,
    ) -> None:
        self._state = global_state
        self._bus = message_bus
        self.agent_id = agent_id
        self._is_backup = is_backup
        # Tracks if this instance was PROMOTED from backup — used to trigger self-failback
        # when original primary returns. False for born-primary instances.
        self._original_role_was_backup: bool = False
        # The exact agent_id of the original primary we pair with (e.g. LIVE-INTEL-PRIMARY).
        # Derived from our own agent_id so we never confuse MANAGER-PRIMARY etc.
        self._expected_primary_id: Optional[str] = (
            agent_id.replace("BACKUP", "PRIMARY") if is_backup else None
        )

        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_primary_heartbeat: float = datetime.now(timezone.utc).timestamp()

        # In-memory diagnostics cache
        self.health_scores: Dict[str, int] = {}
        self.active_anomalies: List[Dict[str, Any]] = []
        self.recommendation_history: List[Dict[str, Any]] = []

        logger.info(
            "[LiveIntelAgent] Constructed. ID=%s (Backup=%s)",
            self.agent_id, self._is_backup
        )

    async def start(self) -> None:
        """Start the monitoring loop and subscribe to the bus."""
        self._running = True

        # Register health status with global state
        reg_type = AgentType.STANDBY if self._is_backup else AgentType.LIVE_INTEL
        await self._state.register_agent(reg_type, self.agent_id)
        await self._state.update_agent_status(reg_type, AgentStatus.HEALTHY)

        # Subscribe to receive heartbeats or instructions
        await self._bus.subscribe(reg_type, self._handle_message)

        # Launch background loop
        self._monitor_task = asyncio.create_task(self._observability_loop())
        logger.info("[LiveIntelAgent] Started. ID=%s", self.agent_id)

    async def stop(self) -> None:
        """Gracefully shut down the agent."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        reg_type = AgentType.STANDBY if self._is_backup else AgentType.LIVE_INTEL
        await self._state.update_agent_status(reg_type, AgentStatus.OFFLINE)
        logger.info("[LiveIntelAgent] Stopped. ID=%s", self.agent_id)

    async def _handle_message(self, message: Message) -> None:
        """Process incoming messages from message bus."""
        if not self._running:
            return

        if not message.verify_integrity():
            logger.error("[LiveIntelAgent] Message integrity verification failed.")
            return

        # Backup agent listens for primary heartbeats
        if self._is_backup and message.message_type == "LIVE_INTEL_HEARTBEAT":
            self._last_primary_heartbeat = datetime.now(timezone.utc).timestamp()
            logger.debug("[LiveIntelAgent Backup] Heartbeat received from %s", message.payload.get("agent_id"))

    async def _observability_loop(self) -> None:
        """Continuous background monitoring task."""
        while self._running:
            try:
                if self._is_backup:
                    await self._run_backup_logic()
                else:
                    await self._run_primary_logic()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[LiveIntelAgent] Error in monitor loop: %s", exc, exc_info=True)
            
            await asyncio.sleep(1.0)

    async def _run_backup_logic(self) -> None:
        """Stands by and monitors the primary instance health."""
        now = datetime.now(timezone.utc).timestamp()
        # Verify heartbeat freshness or check GlobalState status
        primary_health = self._state._agents.get(AgentType.LIVE_INTEL.value)
        
        primary_offline = primary_health is None or primary_health.status == AgentStatus.OFFLINE
        heartbeat_timeout = (now - self._last_primary_heartbeat) > 2.5

        if primary_offline or heartbeat_timeout:
            logger.warning(
                "[LiveIntelAgent Backup] Primary Live Intel is offline or lost heartbeat. Promoting backup to Primary!"
            )
            await self._promote_to_primary()

    async def _run_primary_logic(self) -> None:
        """Active primary diagnostics: health scoring, anomaly detection, recommendations."""
        # 1. Publish primary heartbeat
        heartbeat_msg = Message(
            sender=AgentType.LIVE_INTEL,
            receiver=AgentType.STANDBY,
            message_type="LIVE_INTEL_HEARTBEAT",
            payload={"agent_id": self.agent_id, "timestamp": datetime.now(timezone.utc).isoformat()},
            priority=Priority.P5_BACKGROUND
        )
        await self._bus.publish(heartbeat_msg)

        # 2. Read state and bus metrics
        bus_stats = self._bus.stats()
        
        # 3. Calculate health scores for all system agents
        for agent_type in [
            AgentType.MANAGER,
            AgentType.SCOUT,
            AgentType.VALIDATOR,
            AgentType.GB,
            AgentType.CHECKPOINT_ENGINE,
            AgentType.NOTICER,
            AgentType.CDC_ENGINE
        ]:
            health_entry = self._state._agents.get(agent_type.value)
            score = self._calculate_agent_health(agent_type, health_entry, bus_stats)
            self.health_scores[agent_type.value] = score
            logger.debug("[LiveIntelAgent] Agent %s Health Score: %d", agent_type.value, score)

        # 4. Anomaly detection & Root Cause Analysis
        anomalies = self._analyze_anomalies(bus_stats)
        self.active_anomalies = anomalies

        # 5. Alert Manager for critical issues
        for anomaly in anomalies:
            if anomaly["severity"] == "CRITICAL":
                # Check if we already sent this recommendation recently to avoid spamming
                if anomaly not in self.recommendation_history:
                    self.recommendation_history.append(anomaly)
                    
                    logger.warning("[LiveIntelAgent] Alerting Manager on anomaly: %s", anomaly["description"])
                    warning_msg = Message(
                        sender=AgentType.LIVE_INTEL,
                        receiver=AgentType.MANAGER,
                        message_type=MessageType.LOOP_WARNING,
                        payload={
                            "anomaly_type": anomaly["type"],
                            "description": anomaly["description"],
                            "recommendation": anomaly["recommendation"],
                            "severity": anomaly["severity"]
                        },
                        project_id=anomaly.get("project_id"),
                        migration_id=anomaly.get("migration_id"),
                        priority=Priority.P0_SYSTEM_CRITICAL
                    )
                    await self._bus.publish(warning_msg)

        # 6. Auto-failover and Repair Coordinator
        await self._manage_failovers_and_repairs()

        # 7. If this instance was promoted from backup, check if original primary
        #    has returned so we can self-demote and restore original order.
        if self._original_role_was_backup:
            await self._check_and_trigger_self_failback()

    async def _promote_to_primary(self) -> None:
        """Transition from backup standby to active primary."""
        old_reg_type = AgentType.STANDBY
        new_reg_type = AgentType.LIVE_INTEL

        # Unsubscribe standby queue and subscribe primary queue
        await self._bus.unsubscribe(old_reg_type)
        await self._state.update_agent_status(old_reg_type, AgentStatus.OFFLINE)

        self._is_backup = False
        self._original_role_was_backup = True   # Remember we came from backup
        await self._state.register_agent(new_reg_type, self.agent_id)
        await self._state.update_agent_status(new_reg_type, AgentStatus.HEALTHY)
        await self._bus.subscribe(new_reg_type, self._handle_message)

        logger.critical(
            "[LiveIntelAgent] Backup %s promoted to PRIMARY. Monitoring initialized.",
            self.agent_id
        )

    async def _check_and_trigger_self_failback(self) -> None:
        """
        When this promoted-backup is acting as primary, it continuously checks
        whether the original LIVE-INTEL primary has returned (STANDBY/HEALTHY).
        Uses the stored _expected_primary_id so it ONLY matches 'LIVE-INTEL-PRIMARY'
        and never confuses other primaries like MANAGER-PRIMARY.
        """
        if not self._expected_primary_id:
            return
        original_primary = self._state._agent_instances.get(self._expected_primary_id)
        if original_primary is None:
            return
        if original_primary.status in (
            AgentStatus.STANDBY, AgentStatus.HEALTHY, AgentStatus.IDLE
        ):
            logger.critical(
                "[LiveIntelAgent Failback] Original Primary '%s' is back online! "
                "Self-demoting '%s' back to Backup — restoring original order.",
                original_primary.agent_id,
                self.agent_id,
            )
            await self._demote_self_to_backup(original_primary.agent_id)

    async def _demote_self_to_backup(self, original_primary_id: str) -> None:
        """
        Self-demotion: resign from the primary role, restore the original primary
        to LIVE_INTEL HEALTHY, and re-register self as STANDBY backup.
        This is the symmetric reverse of _promote_to_primary.
        """
        # 1. Resign from primary monitoring role
        await self._bus.unsubscribe(AgentType.LIVE_INTEL)
        await self._state.update_agent_status(AgentType.LIVE_INTEL, AgentStatus.OFFLINE)

        # 2. Restore the original primary as the active Live Intel
        await self._state.register_agent(AgentType.LIVE_INTEL, original_primary_id)
        await self._state.update_agent_status(
            AgentType.LIVE_INTEL, AgentStatus.HEALTHY, original_primary_id
        )

        # 3. Re-register self as backup standby
        self._is_backup = True
        self._original_role_was_backup = False
        await self._state.register_agent(AgentType.STANDBY, self.agent_id)
        await self._state.update_agent_status(AgentType.STANDBY, AgentStatus.STANDBY)
        await self._bus.subscribe(AgentType.STANDBY, self._handle_message)

        logger.critical(
            "[LiveIntelAgent] Self-demotion COMPLETE — '%s' restored as PRIMARY. "
            "'%s' returned to BACKUP standby.",
            original_primary_id,
            self.agent_id,
        )

    def _calculate_agent_health(
        self,
        agent_type: AgentType,
        health_entry: Optional[Any],
        bus_stats: Dict[str, Any]
    ) -> int:
        """
        Dynamically calculate agent health score between 0 and 100.
        """
        if not health_entry:
            return 0
        if health_entry.status == AgentStatus.OFFLINE:
            return 0

        score = 100

        # Subtract for errors
        score -= min(40, health_entry.error_count * 15)

        # Subtract for queue depth (backlog)
        q_depths = bus_stats.get("queue_depths", {})
        depth = q_depths.get(agent_type.value, 0)
        if depth > 0:
            score -= min(25, depth * 5)

        # Subtract for busy status if no task progress
        if health_entry.status == AgentStatus.FAILED:
            score -= 50
        elif health_entry.status == AgentStatus.RECOVERING:
            score -= 25

        # Check last heartbeat freshness
        if health_entry.last_heartbeat:
            try:
                last_hb = datetime.fromisoformat(health_entry.last_heartbeat)
                delta = (datetime.now(timezone.utc) - last_hb).total_seconds()
                if delta > 3.0:
                    score -= min(30, int(delta * 5))
            except Exception:
                pass

        return max(0, min(100, score))

    def _analyze_anomalies(self, bus_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify anomalies and suggest repair actions."""
        anomalies = []
        
        # 1. Queue backlog check
        q_depths = bus_stats.get("queue_depths", {})
        for agent_val, depth in q_depths.items():
            if depth >= 5:
                anomalies.append({
                    "type": "QUEUE_BACKLOG",
                    "agent": agent_val,
                    "severity": "WARNING",
                    "description": f"Agent {agent_val} has a large queue backlog of {depth} messages.",
                    "recommendation": f"Scale resources or restart agent {agent_val}."
                })

        # 2. Incident analysis
        for project_id, project in self._state._projects.items():
            open_incidents = self._state.get_open_incidents(project_id)
            if open_incidents:
                for inc in open_incidents:
                    if not inc.is_resolved:
                        # Validation failure anomalies
                        if "VALIDATION_FAILED" in inc.failure_reason or "validation" in inc.description.lower():
                            anomalies.append({
                                "type": "VALIDATION_ERROR",
                                "project_id": project_id,
                                "migration_id": inc.migration_id,
                                "severity": "CRITICAL",
                                "description": f"Project {project_id} validation stage failed: {inc.description}",
                                "recommendation": "INTEGRITY ERROR: Verify schema matching and re-validate database target config."
                            })
                        elif "CHECKSUM_MISMATCH" in inc.failure_reason:
                            anomalies.append({
                                "type": "CHECKSUM_ERROR",
                                "project_id": project_id,
                                "migration_id": inc.migration_id,
                                "severity": "CRITICAL",
                                "description": f"Project {project_id} checksum mismatch: {inc.description}",
                                "recommendation": "INTEGRITY ERROR: Re-run Scout to refresh checksum, and re-run validation."
                            })
                        elif "PERMISSION" in inc.failure_reason or "readonly" in inc.description.lower():
                            anomalies.append({
                                "type": "PERMISSION_ERROR",
                                "project_id": project_id,
                                "migration_id": inc.migration_id,
                                "severity": "CRITICAL",
                                "description": f"Project {project_id} safety violation: {inc.description}",
                                "recommendation": "SAFETY VIOLATION: Ensure database configuration credentials are read-only."
                            })
                        else:
                            anomalies.append({
                                "type": "UNKNOWN_ERROR",
                                "project_id": project_id,
                                "migration_id": inc.migration_id,
                                "severity": "WARNING",
                                "description": f"Active incident in project {project_id}: {inc.description}",
                                "recommendation": "INVESTIGATE: Manually check agent execution traces and logs."
                            })

        return anomalies

    async def _manage_failovers_and_repairs(self) -> None:
        """
        Scan all agent instances to detect failures on primary instances,
        promote standby backups, execute repairs, and trigger failback when restored.
        """
        agent_types = [
            AgentType.MANAGER,
            AgentType.SCOUT,
            AgentType.VALIDATOR,
            AgentType.GB,
            AgentType.CHECKPOINT_ENGINE,
            AgentType.NOTICER,
            AgentType.CDC_ENGINE
        ]

        for at in agent_types:
            # Gather instances of this type registered in global state
            instances = [
                inst for inst in self._state._agent_instances.values()
                if inst.agent_type == at
            ]
            if len(instances) < 2:
                continue

            primary = next((i for i in instances if "backup" not in i.agent_id.lower() and "standby" not in i.agent_id.lower()), None)
            backup = next((i for i in instances if "backup" in i.agent_id.lower() or "standby" in i.agent_id.lower()), None)

            if not primary or not backup:
                continue

            active_routing = self._state.get_agent_health(at)

            # Scenario A: Primary failed or offline, but currently mapped as active
            if primary.status in (AgentStatus.FAILED, AgentStatus.OFFLINE) and active_routing.agent_id == primary.agent_id:
                if backup.status == AgentStatus.STANDBY:
                    logger.critical(
                        "[LiveIntelAgent Failover] Primary agent %s (%s) is %s! Promoting backup (%s) to active primary.",
                        at.value, primary.agent_id, primary.status.value, backup.agent_id
                    )
                    # 1. Promote backup
                    promo_msg = Message(
                        sender=AgentType.LIVE_INTEL,
                        receiver=at,
                        message_type="PROMOTION",
                        payload={"target_agent_id": backup.agent_id},
                        priority=Priority.P0_SYSTEM_CRITICAL
                    )
                    await self._bus.publish(promo_msg)
                    await self._state.promote_agent_instance(at, backup.agent_id)

                    # 2. Repair primary
                    logger.critical("[LiveIntelAgent Repair] Dispatching repair instruction to primary agent %s (%s).", at.value, primary.agent_id)
                    repair_msg = Message(
                        sender=AgentType.LIVE_INTEL,
                        receiver=at,
                        message_type="REPAIR",
                        payload={"target_agent_id": primary.agent_id},
                        priority=Priority.P0_SYSTEM_CRITICAL
                    )
                    await self._bus.publish(repair_msg)

            # Scenario B: Primary is now repaired and in STANDBY, but Backup is currently mapped as active (Failback)
            elif primary.status in (AgentStatus.STANDBY, AgentStatus.HEALTHY, AgentStatus.IDLE) and active_routing.agent_id == backup.agent_id:
                logger.critical(
                    "[LiveIntelAgent Failback] Primary agent %s (%s) has been repaired and is online! Demoting backup (%s) and failing back to primary.",
                    at.value, primary.agent_id, backup.agent_id
                )
                # 1. Promote primary
                promo_msg = Message(
                    sender=AgentType.LIVE_INTEL,
                    receiver=at,
                    message_type="PROMOTION",
                    payload={"target_agent_id": primary.agent_id},
                    priority=Priority.P0_SYSTEM_CRITICAL
                )
                await self._bus.publish(promo_msg)
                await self._state.promote_agent_instance(at, primary.agent_id)

                # 2. Demote backup back to standby
                demo_msg = Message(
                    sender=AgentType.LIVE_INTEL,
                    receiver=at,
                    message_type="DEMOTION",
                    payload={"target_agent_id": backup.agent_id},
                    priority=Priority.P0_SYSTEM_CRITICAL
                )
                await self._bus.publish(demo_msg)
