"""
akaalEngine.runtime.models.task
================================
Canonical Task models, TaskState FSM validation, TaskSpec, and TaskSnapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from akaalEngine.runtime.models.errors import InvalidTaskTransitionError


class TaskState(str, Enum):
    """
    Canonical 10-state validated Task Lifecycle FSM.
    """
    PENDING = "PENDING"
    ADMITTED = "ADMITTED"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


# Permitted state transitions table
_VALID_TASK_TRANSITIONS: Dict[TaskState, Sequence[TaskState]] = {
    TaskState.PENDING: (TaskState.ADMITTED, TaskState.CANCELLING, TaskState.CANCELLED, TaskState.ABANDONED),
    TaskState.ADMITTED: (TaskState.ASSIGNED, TaskState.CANCELLING, TaskState.CANCELLED, TaskState.FAILED, TaskState.ABANDONED),
    TaskState.ASSIGNED: (TaskState.RUNNING, TaskState.CANCELLING, TaskState.CANCELLED, TaskState.FAILED, TaskState.ABANDONED),
    TaskState.RUNNING: (TaskState.PAUSED, TaskState.CANCELLING, TaskState.CANCELLED, TaskState.SUCCEEDED, TaskState.FAILED, TaskState.ABANDONED),
    TaskState.PAUSED: (TaskState.RUNNING, TaskState.CANCELLING, TaskState.CANCELLED, TaskState.FAILED, TaskState.ABANDONED),
    TaskState.CANCELLING: (TaskState.CANCELLED, TaskState.FAILED, TaskState.ABANDONED),
    TaskState.CANCELLED: (),
    TaskState.SUCCEEDED: (),
    TaskState.FAILED: (TaskState.PENDING,),  # Allows explicit retry restart if cleared
    TaskState.ABANDONED: (TaskState.PENDING,),
}


def validate_task_transition(task_id: str, current_state: TaskState, target_state: TaskState) -> None:
    """Validates that current_state -> target_state is a legal FSM transition."""
    if current_state == target_state:
        return
    allowed = _VALID_TASK_TRANSITIONS.get(current_state, ())
    if target_state not in allowed:
        raise InvalidTaskTransitionError(task_id, current_state.value, target_state.value)


@dataclass(frozen=True)
class TaskSpec:
    """
    Immutable Task Specification submitted to Runtime Authority.
    """
    task_id: str
    task_type: str
    func: Optional[Callable[..., Any]] = None
    args: Sequence[Any] = field(default_factory=tuple)
    kwargs: Mapping[str, Any] = field(default_factory=dict)
    required_capabilities: Sequence[str] = field(default_factory=tuple)
    cpu_cores_required: float = 1.0
    memory_mb_required: float = 512.0
    weight: int = 1
    allow_pause: bool = True
    allow_cancellation: bool = True
    is_recoverable: bool = False  # Task must explicitly declare if it is replay-safe/idempotent
    process_isolated: bool = False
    timeout_seconds: Optional[float] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "required_capabilities": list(self.required_capabilities),
            "cpu_cores_required": self.cpu_cores_required,
            "memory_mb_required": self.memory_mb_required,
            "weight": self.weight,
            "allow_pause": self.allow_pause,
            "allow_cancellation": self.allow_cancellation,
            "is_recoverable": self.is_recoverable,
            "process_isolated": self.process_isolated,
            "timeout_seconds": self.timeout_seconds,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TaskSnapshot:
    """
    Immutable snapshot of task state at a specific point in time.
    """
    task_id: str
    task_type: str
    state: TaskState
    worker_id: Optional[str] = None
    lease_id: Optional[str] = None
    attempt_id: Optional[str] = None  # Immutable execution attempt identity (worker + fencing epoch + attempt #)
    fencing_epoch: int = 0
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.state in (TaskState.CANCELLED, TaskState.SUCCEEDED, TaskState.FAILED, TaskState.ABANDONED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "state": self.state.value,
            "worker_id": self.worker_id,
            "lease_id": self.lease_id,
            "attempt_id": self.attempt_id,
            "fencing_epoch": self.fencing_epoch,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "is_terminal": self.is_terminal,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "metadata": dict(self.metadata),
        }
