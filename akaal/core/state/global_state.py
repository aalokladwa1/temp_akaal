"""
NexusForge — Global State Manager
====================================
Maintains the authoritative system-wide state for all active projects,
agents, checkpoints, incidents, and queues.

brain.md Section 5: Global State Model
  - Active Projects
  - Active Migrations
  - Agent Health Map
  - Checkpoint Registry
  - Validation Status Map
  - Incident Registry
  - Resource Utilization Map
  - Execution Queue Map

The global state is the single source of truth for the Manager Agent.
No state modification may occur without going through this manager.
All mutations are atomic and logged.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.models.enums import AgentStatus, AgentType, WorkflowState
from akaal.core.models.project import IncidentRecord, MigrationProject, MigrationSession

logger = logging.getLogger("nexusforge.global_state")


# ---------------------------------------------------------------------------
# Agent Health Entry
# ---------------------------------------------------------------------------

class AgentHealthEntry:
    """Tracks health and status for a registered agent."""
    def __init__(self, agent_type: AgentType, agent_id: str) -> None:
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.status = AgentStatus.IDLE
        self.last_heartbeat: Optional[str] = None
        self.current_task_id: Optional[str] = None
        self.current_project_id: Optional[str] = None
        self.error_count: int = 0
        self.registered_at = datetime.now(timezone.utc).isoformat()

    def update_heartbeat(self) -> None:
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()

    def set_status(self, status: AgentStatus) -> None:
        self.status = status
        self.update_heartbeat()

    def is_available(self) -> bool:
        return self.status in (AgentStatus.IDLE, AgentStatus.HEALTHY)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type.value,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "current_task_id": self.current_task_id,
            "current_project_id": self.current_project_id,
            "error_count": self.error_count,
            "registered_at": self.registered_at,
        }


# ---------------------------------------------------------------------------
# Checkpoint Registry Entry
# ---------------------------------------------------------------------------

class CheckpointEntry:
    """Lightweight checkpoint reference stored in global state."""
    def __init__(
        self,
        checkpoint_id: str,
        project_id: str,
        migration_id: str,
        workflow_state: WorkflowState,
        description: str,
    ) -> None:
        self.checkpoint_id = checkpoint_id
        self.project_id = project_id
        self.migration_id = migration_id
        self.workflow_state = workflow_state
        self.description = description
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.is_valid = True

    def invalidate(self) -> None:
        self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "workflow_state": self.workflow_state.value,
            "description": self.description,
            "created_at": self.created_at,
            "is_valid": self.is_valid,
        }


# ---------------------------------------------------------------------------
# Global State
# ---------------------------------------------------------------------------

class GlobalState:
    """
    Thread-safe (asyncio-safe) global state container.

    This is the single authoritative state store for the NexusForge system.
    All reads and writes go through this class.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

        # Active projects: project_id → MigrationProject
        self._projects: Dict[str, MigrationProject] = {}

        # Active sessions: migration_id → MigrationSession
        self._sessions: Dict[str, MigrationSession] = {}

        # Agent health: agent_type.value → AgentHealthEntry (currently active agent of each type)
        self._agents: Dict[str, AgentHealthEntry] = {}
        # All agent instances: agent_id → AgentHealthEntry
        self._agent_instances: Dict[str, AgentHealthEntry] = {}

        # Checkpoint registry: checkpoint_id → CheckpointEntry
        self._checkpoints: Dict[str, CheckpointEntry] = {}

        # Incident registry: incident_id → IncidentRecord
        self._incidents: Dict[str, IncidentRecord] = {}

        # Validation status map: project_id → list of validation result dicts
        self._validation_history: Dict[str, List[Dict[str, Any]]] = {}

        # System frozen flag (Loop Governor freeze)
        self._system_frozen: bool = False
        self._freeze_reason: Optional[str] = None

        logger.info("[GlobalState] Initialized.")

    # ------------------------------------------------------------------
    # System Freeze
    # ------------------------------------------------------------------

    async def freeze_system(self, reason: str) -> None:
        """
        Emergency freeze — stop all new work.
        Triggered by Loop Governor when state_hash repeats 4+ times.
        """
        async with self._lock:
            self._system_frozen = True
            self._freeze_reason = reason
        logger.critical("[GlobalState] SYSTEM FROZEN. Reason: %s", reason)

    def is_frozen(self) -> bool:
        return self._system_frozen

    def freeze_reason(self) -> Optional[str]:
        return self._freeze_reason

    async def unfreeze_system(self) -> None:
        """Unfreeze after human intervention / successful recovery."""
        async with self._lock:
            self._system_frozen = False
            self._freeze_reason = None
        logger.info("[GlobalState] System unfrozen.")

    # ------------------------------------------------------------------
    # Project Management
    # ------------------------------------------------------------------

    async def register_project(self, project: MigrationProject) -> None:
        """Register a new migration project."""
        async with self._lock:
            if project.project_id in self._projects:
                raise ValueError(
                    f"Project {project.project_id} already registered. "
                    "Duplicate projects are rejected (TRD Section 13)."
                )
            self._projects[project.project_id] = project
        logger.info("[GlobalState] Project registered: %s (%s)", project.name, project.project_id)

    async def get_project(self, project_id: str) -> Optional[MigrationProject]:
        return self._projects.get(project_id)

    async def update_project_state(
        self,
        project_id: str,
        new_state: WorkflowState,
        reason: str = "",
    ) -> None:
        """Atomically update project workflow state with history logging."""
        async with self._lock:
            project = self._projects.get(project_id)
            if not project:
                raise ValueError(f"Project not found: {project_id}")
            project.transition_to(new_state, reason)
        logger.info(
            "[GlobalState] Project %s → state=%s reason=%s",
            project_id, new_state.value, reason
        )

    def get_all_projects(self) -> Dict[str, MigrationProject]:
        return dict(self._projects)

    def get_active_projects(self) -> List[MigrationProject]:
        return [
            p for p in self._projects.values()
            if not p.is_terminal()
        ]

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    async def register_session(self, session: MigrationSession) -> None:
        async with self._lock:
            self._sessions[session.migration_id] = session
        logger.info("[GlobalState] Session registered: %s", session.migration_id)

    async def get_session(self, migration_id: str) -> Optional[MigrationSession]:
        return self._sessions.get(migration_id)

    # ------------------------------------------------------------------
    # Agent Registry
    # ------------------------------------------------------------------

    async def register_agent(self, agent_type: AgentType, agent_id: str) -> AgentHealthEntry:
        """Register an agent in the health map."""
        async with self._lock:
            entry = AgentHealthEntry(agent_type, agent_id)
            self._agent_instances[agent_id] = entry
            # Register as active if it's the first registration or if the current active is offline/failed
            active_entry = self._agents.get(agent_type.value)
            if active_entry is None or active_entry.status in (AgentStatus.OFFLINE, AgentStatus.FAILED):
                self._agents[agent_type.value] = entry
        logger.info("[GlobalState] Agent registered: %s (id=%s)", agent_type.value, agent_id)
        return entry

    async def update_agent_status(self, agent_type: AgentType, status: AgentStatus, agent_id: Optional[str] = None) -> None:
        async with self._lock:
            if agent_id and agent_id in self._agent_instances:
                entry = self._agent_instances[agent_id]
                entry.set_status(status)
                active_entry = self._agents.get(agent_type.value)
                if active_entry and active_entry.agent_id == agent_id:
                    active_entry.set_status(status)
            else:
                entry = self._agents.get(agent_type.value)
                if entry:
                    entry.set_status(status)
                    if entry.agent_id in self._agent_instances:
                        self._agent_instances[entry.agent_id].set_status(status)
        logger.debug("[GlobalState] Agent %s status → %s", agent_type.value, status.value)

    async def promote_agent_instance(self, agent_type: AgentType, agent_id: str) -> None:
        """Promote an instance to be the active primary agent in the routing map."""
        async with self._lock:
            entry = self._agent_instances.get(agent_id)
            if entry:
                self._agents[agent_type.value] = entry
                entry.set_status(AgentStatus.HEALTHY)
        logger.info("[GlobalState] Promoted agent instance %s to active for %s", agent_id, agent_type.value)

    def get_agent_health(self, agent_type: AgentType) -> Optional[AgentHealthEntry]:
        return self._agents.get(agent_type.value)

    def get_agent_instance_health(self, agent_id: str) -> Optional[AgentHealthEntry]:
        return self._agent_instances.get(agent_id)

    def is_agent_available(self, agent_type: AgentType) -> bool:
        entry = self._agents.get(agent_type.value)
        return entry.is_available() if entry else False

    def get_all_agent_health(self) -> Dict[str, Dict[str, Any]]:
        return {k: v.to_dict() for k, v in self._agent_instances.items()}

    # ------------------------------------------------------------------
    # Checkpoint Registry
    # ------------------------------------------------------------------

    async def register_checkpoint(self, entry: CheckpointEntry) -> None:
        async with self._lock:
            self._checkpoints[entry.checkpoint_id] = entry
        logger.info(
            "[GlobalState] Checkpoint registered: %s project=%s state=%s",
            entry.checkpoint_id, entry.project_id, entry.workflow_state.value
        )

    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointEntry]:
        return self._checkpoints.get(checkpoint_id)

    def get_latest_checkpoint(self, project_id: str) -> Optional[CheckpointEntry]:
        """Return the most recently created valid checkpoint for a project."""
        project_checkpoints = [
            c for c in self._checkpoints.values()
            if c.project_id == project_id and c.is_valid
        ]
        if not project_checkpoints:
            return None
        return max(project_checkpoints, key=lambda c: c.created_at)

    def get_all_checkpoints(self, project_id: str) -> List[CheckpointEntry]:
        return [
            c for c in self._checkpoints.values()
            if c.project_id == project_id
        ]

    # ------------------------------------------------------------------
    # Incident Registry
    # ------------------------------------------------------------------

    async def register_incident(self, incident: IncidentRecord) -> None:
        async with self._lock:
            self._incidents[incident.incident_id] = incident
        logger.warning(
            "[GlobalState] Incident registered: %s severity=%s reason=%s",
            incident.incident_id, incident.severity, incident.failure_reason
        )

    async def resolve_incident(self, incident_id: str, notes: str = "") -> None:
        async with self._lock:
            incident = self._incidents.get(incident_id)
            if incident:
                incident.resolve(notes)
        logger.info("[GlobalState] Incident resolved: %s", incident_id)

    def get_open_incidents(self, project_id: Optional[str] = None) -> List[IncidentRecord]:
        incidents = [i for i in self._incidents.values() if not i.is_resolved]
        if project_id:
            incidents = [i for i in incidents if i.project_id == project_id]
        return incidents

    def get_all_incidents(self) -> Dict[str, IncidentRecord]:
        return dict(self._incidents)

    # ------------------------------------------------------------------
    # Validation History
    # ------------------------------------------------------------------

    async def record_validation(
        self,
        project_id: str,
        validation_type: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        async with self._lock:
            if project_id not in self._validation_history:
                self._validation_history[project_id] = []
            self._validation_history[project_id].append({
                "type": validation_type,
                "result": result,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def get_validation_history(self, project_id: str) -> List[Dict[str, Any]]:
        return self._validation_history.get(project_id, [])

    # ------------------------------------------------------------------
    # System Snapshot (Observability)
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a full diagnostic snapshot of global state."""
        return {
            "system_frozen": self._system_frozen,
            "freeze_reason": self._freeze_reason,
            "total_projects": len(self._projects),
            "active_projects": len(self.get_active_projects()),
            "total_sessions": len(self._sessions),
            "total_checkpoints": len(self._checkpoints),
            "total_incidents": len(self._incidents),
            "open_incidents": len(self.get_open_incidents()),
            "agents": self.get_all_agent_health(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_global_state: Optional[GlobalState] = None


def get_global_state() -> GlobalState:
    """Return the global singleton GlobalState instance."""
    global _global_state
    if _global_state is None:
        _global_state = GlobalState()
    return _global_state


def reset_global_state() -> None:
    """Reset the singleton (tests only)."""
    global _global_state
    _global_state = None
