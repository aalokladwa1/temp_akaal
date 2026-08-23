"""
akaalEngine.runtime
===================
Canonical Runtime Authority (#6).
Exposes RuntimeAuthority, TaskSpec, TaskSnapshot, TaskState, WorkerSpec, WorkerSnapshot, WorkerState.
"""

from akaalEngine.runtime.api import RuntimeAuthority
from akaalEngine.runtime.models import (
    FencingRejectedError,
    InvalidTaskTransitionError,
    LeaseExpiredError,
    PauseUnsupportedError,
    ResourceAdmissionError,
    ResourceBudget,
    ResourceRequirement,
    RuntimeEngineException,
    RuntimeNotStartedError,
    RuntimeShuttingDownError,
    TaskExecutionError,
    TaskNotFoundError,
    TaskRejectedError,
    TaskSnapshot,
    TaskSpec,
    TaskState,
    WorkerCapability,
    WorkerHeartbeat,
    WorkerNotFoundError,
    WorkerSnapshot,
    WorkerSpec,
    WorkerState,
    validate_task_transition,
)

__all__ = [
    "RuntimeAuthority",
    "TaskSpec",
    "TaskSnapshot",
    "TaskState",
    "validate_task_transition",
    "WorkerSpec",
    "WorkerSnapshot",
    "WorkerState",
    "WorkerCapability",
    "WorkerHeartbeat",
    "ResourceBudget",
    "ResourceRequirement",
    "RuntimeEngineException",
    "RuntimeNotStartedError",
    "RuntimeShuttingDownError",
    "TaskNotFoundError",
    "WorkerNotFoundError",
    "InvalidTaskTransitionError",
    "TaskRejectedError",
    "ResourceAdmissionError",
    "FencingRejectedError",
    "LeaseExpiredError",
    "TaskExecutionError",
    "PauseUnsupportedError",
]
