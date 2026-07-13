"""
NexusForge — Task & Assignment Models
=======================================
Defines the Task contract for inter-agent work assignment.

manager_agent.md Section 7: Each task must include:
  Task ID, Agent ID, Migration ID, Priority level,
  Execution constraints, Timeout value, Checkpoint reference.

No agent may begin work without a formally structured Task.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.models.enums import AgentType, Priority, TaskType


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Task Status
# ---------------------------------------------------------------------------

class TaskStatus:
    PENDING    = "PENDING"
    ASSIGNED   = "ASSIGNED"
    RUNNING    = "RUNNING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"
    RETRYING   = "RETRYING"
    TIMED_OUT  = "TIMED_OUT"


# ---------------------------------------------------------------------------
# Task Definition
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """
    A unit of work assigned by the Manager to an agent.

    Every task is fully self-describing — agents must not need
    external context to understand what they are asked to do.

    TRD Section 13 Queue Management: each queue item supports
    Priority, Retry, Cancellation, Pause, Resume, Timeout.
    """

    # Core identity
    task_type: TaskType
    assigned_to: AgentType
    project_id: str
    migration_id: str

    # Auto-generated
    task_id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_utc_now)
    created_by: AgentType = AgentType.MANAGER

    # Execution constraints (manager_agent.md Section 7)
    priority: Priority = Priority.P3_DISCOVERY
    timeout_seconds: int = 300                      # Default 5 min
    max_retries: int = 3
    retry_count: int = 0
    checkpoint_ref: Optional[str] = None            # Checkpoint to restore from if needed

    # Payload — task-specific parameters
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Lifecycle
    status: str = TaskStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    result_ref: Optional[str] = None                # Reference to output artifact

    def assign(self) -> None:
        """Mark task as assigned."""
        self.status = TaskStatus.ASSIGNED

    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = _utc_now()

    def complete(self, result_ref: Optional[str] = None) -> None:
        """Mark task as successfully completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = _utc_now()
        self.result_ref = result_ref

    def fail(self, reason: str) -> None:
        """Mark task as failed with reason."""
        self.status = TaskStatus.FAILED
        self.completed_at = _utc_now()
        self.failure_reason = reason

    def cancel(self) -> None:
        """Cancel task."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = _utc_now()

    def increment_retry(self) -> bool:
        """
        Increment retry counter.
        Returns True if retry is allowed, False if max retries exceeded.
        """
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            return False
        self.status = TaskStatus.RETRYING
        return True

    def is_timed_out(self) -> bool:
        """Check if this task has exceeded its timeout since starting."""
        if not self.started_at:
            return False
        start = datetime.fromisoformat(self.started_at)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        return elapsed > self.timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "assigned_to": self.assigned_to.value,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "priority": self.priority.value,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "checkpoint_ref": self.checkpoint_ref,
            "parameters": self.parameters,
            "status": self.status,
            "created_at": self.created_at,
            "created_by": self.created_by.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failure_reason": self.failure_reason,
            "result_ref": self.result_ref,
        }

    def __repr__(self) -> str:
        return (
            f"Task(id={self.task_id[:8]}..., "
            f"type={self.task_type.value}, "
            f"agent={self.assigned_to.value}, "
            f"status={self.status})"
        )


# ---------------------------------------------------------------------------
# Task Result — returned by agents to Manager
# ---------------------------------------------------------------------------

@dataclass
class TaskResult:
    """
    The structured result returned by an agent after completing (or failing) a task.
    Manager uses this to drive next workflow transitions.
    """
    task_id: str
    project_id: str
    migration_id: str
    agent_type: AgentType
    success: bool
    result_id: str = field(default_factory=_new_id)
    completed_at: str = field(default_factory=_utc_now)

    # Result payload — agent-specific
    output: Dict[str, Any] = field(default_factory=dict)

    # Failure details
    failure_reason: Optional[str] = None
    error_message: Optional[str] = None
    is_recoverable: bool = True

    # Metrics
    duration_seconds: Optional[float] = None
    objects_processed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "agent_type": self.agent_type.value,
            "success": self.success,
            "completed_at": self.completed_at,
            "output": self.output,
            "failure_reason": self.failure_reason,
            "error_message": self.error_message,
            "is_recoverable": self.is_recoverable,
            "duration_seconds": self.duration_seconds,
            "objects_processed": self.objects_processed,
        }
