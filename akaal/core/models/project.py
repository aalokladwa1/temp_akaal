"""
NexusForge — Migration Project & Session Models
=================================================
Data models representing a migration project, session, and associated metadata.
These are the core data contracts passed between all agents.

TRD Section 13 — Manager creates: Project IDs, Migration IDs, Audit Sessions,
Execution Sessions, Execution Workspace, Checkpoint Repository.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.models.enums import (
    MigrationStrategy,
    SystemType,
    WorkflowState,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Source / Target Connection Config
# (Credentials are NEVER stored here — only references / masked identifiers)
# ---------------------------------------------------------------------------

@dataclass
class ConnectionConfig:
    """
    Connection descriptor for source or target systems.
    Plaintext credentials must NEVER be stored here.
    Use a secrets manager reference (e.g. vault path or env key name).
    TRD Section 13 Security: Manager shall never store plaintext credentials.
    """
    system_type: SystemType
    host: str
    port: int
    database_name: str
    credentials_ref: str        # Reference key to secrets manager, NOT the secret itself
    read_only: bool = True       # Source systems must always be read-only
    extra: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"ConnectionConfig(type={self.system_type.value}, "
            f"host={self.host}:{self.port}, "
            f"db={self.database_name}, "
            f"read_only={self.read_only})"
        )


# ---------------------------------------------------------------------------
# Migration Project
# ---------------------------------------------------------------------------

@dataclass
class MigrationProject:
    """
    Top-level container for a migration.

    Created by Manager Agent on user request (workflow.md Section 4).
    Immutable after creation — updates go through workflow state transitions.
    """
    # Core identity
    name: str
    source_config: ConnectionConfig
    target_config: ConnectionConfig
    strategy: MigrationStrategy

    # Auto-generated
    project_id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_utc_now)
    created_by: str = "system"           # Human identity recorded here on approval

    # Current state
    state: WorkflowState = WorkflowState.IDLE
    state_history: List[Dict[str, str]] = field(default_factory=list)

    # Associated IDs — populated progressively
    active_migration_id: Optional[str] = None
    audit_session_id: Optional[str] = None
    execution_session_id: Optional[str] = None

    # Statistics
    total_objects_discovered: int = 0
    total_objects_migrated: int = 0
    validation_pass_count: int = 0
    validation_fail_count: int = 0

    # Flags
    human_approval_granted: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    def transition_to(self, new_state: WorkflowState, reason: str = "") -> None:
        """
        Record a state transition.
        Every transition is immutably appended to state_history.
        """
        previous = self.state
        self.state = new_state
        self.state_history.append({
            "from": previous.value,
            "to": new_state.value,
            "timestamp": _utc_now(),
            "reason": reason,
        })

    def is_terminal(self) -> bool:
        """Return True if this project is in a terminal (non-resumable) state."""
        return self.state in (
            WorkflowState.MIGRATION_COMPLETED,
            WorkflowState.CANCELLED,
            WorkflowState.ESCALATED,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "strategy": self.strategy.value,
            "state": self.state.value,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "active_migration_id": self.active_migration_id,
            "audit_session_id": self.audit_session_id,
            "execution_session_id": self.execution_session_id,
            "human_approval_granted": self.human_approval_granted,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "total_objects_discovered": self.total_objects_discovered,
            "total_objects_migrated": self.total_objects_migrated,
            "validation_pass_count": self.validation_pass_count,
            "validation_fail_count": self.validation_fail_count,
            "state_history": self.state_history,
        }


# ---------------------------------------------------------------------------
# Migration Session
# (One project can have multiple sessions, e.g. after recovery)
# ---------------------------------------------------------------------------

@dataclass
class MigrationSession:
    """
    Represents a single execution session within a project.
    A new session is created when a migration resumes from checkpoint.
    """
    project_id: str
    session_id: str = field(default_factory=_new_id)
    migration_id: str = field(default_factory=_new_id)
    started_at: str = field(default_factory=_utc_now)
    ended_at: Optional[str] = None

    state: WorkflowState = WorkflowState.IDLE
    checkpoint_count: int = 0
    last_checkpoint_id: Optional[str] = None

    # Batch tracking
    total_batches: int = 0
    completed_batches: int = 0
    failed_batches: int = 0

    def complete(self) -> None:
        self.ended_at = _utc_now()
        self.state = WorkflowState.MIGRATION_COMPLETED

    def duration_seconds(self) -> Optional[float]:
        if not self.ended_at:
            return None
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.ended_at)
        return (end - start).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "session_id": self.session_id,
            "migration_id": self.migration_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "state": self.state.value,
            "checkpoint_count": self.checkpoint_count,
            "last_checkpoint_id": self.last_checkpoint_id,
            "total_batches": self.total_batches,
            "completed_batches": self.completed_batches,
            "failed_batches": self.failed_batches,
        }


# ---------------------------------------------------------------------------
# Human Approval Record
# ---------------------------------------------------------------------------

@dataclass
class ApprovalRecord:
    """
    Immutable record of a human approval decision.
    TRD Section 13: Human identity shall be recorded before approval.
    """
    project_id: str
    migration_id: str
    decision: str                  # ApprovalDecision.value
    decided_by: str                # Human identity (username / email)
    decided_at: str = field(default_factory=_utc_now)
    notes: str = ""
    record_id: str = field(default_factory=_new_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "decision": self.decision,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Incident Record
# ---------------------------------------------------------------------------

@dataclass
class IncidentRecord:
    """
    Auto-created incident for agent failures, validation failures, etc.
    TRD Section 13 Incident Management.
    """
    project_id: str
    migration_id: Optional[str]
    severity: str                    # IncidentSeverity.value
    failure_reason: str              # FailureReason.value
    description: str
    source_agent: str                # AgentType.value
    incident_id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_utc_now)
    resolved_at: Optional[str] = None
    resolution_notes: str = ""
    is_resolved: bool = False

    def resolve(self, notes: str = "") -> None:
        self.is_resolved = True
        self.resolved_at = _utc_now()
        self.resolution_notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "severity": self.severity,
            "failure_reason": self.failure_reason,
            "description": self.description,
            "source_agent": self.source_agent,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolution_notes": self.resolution_notes,
            "is_resolved": self.is_resolved,
        }
