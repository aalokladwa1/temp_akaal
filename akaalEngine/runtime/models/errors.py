"""
akaalEngine.runtime.models.errors
==================================
Canonical normalized exception hierarchy for Authority #6 Runtime.
"""

from typing import Any, Mapping, Optional


class RuntimeEngineException(Exception):
    """Base exception for all Authority #6 Runtime failures."""

    def __init__(self, message: str, error_code: str = "RUNTIME_ERROR", details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(f"[{error_code}] {message}")
        self.message = message
        self.error_code = error_code
        self.details = dict(details or {})


class RuntimeNotStartedError(RuntimeEngineException):
    """Raised when operating on a RuntimeAuthority that has not been started."""
    def __init__(self, message: str = "Runtime Authority is not running.") -> None:
        super().__init__(message, error_code="RUNTIME_NOT_STARTED")


class RuntimeShuttingDownError(RuntimeEngineException):
    """Raised when submitting work while Runtime is shutting down."""
    def __init__(self, message: str = "Runtime Authority is shutting down.") -> None:
        super().__init__(message, error_code="RUNTIME_SHUTTING_DOWN")


class TaskNotFoundError(RuntimeEngineException):
    """Raised when a task ID is not found in Runtime state."""
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task '{task_id}' not found.", error_code="TASK_NOT_FOUND", details={"task_id": task_id})


class WorkerNotFoundError(RuntimeEngineException):
    """Raised when a worker ID is not registered."""
    def __init__(self, worker_id: str) -> None:
        super().__init__(f"Worker '{worker_id}' not found.", error_code="WORKER_NOT_FOUND", details={"worker_id": worker_id})


class InvalidTaskTransitionError(RuntimeEngineException):
    """Raised when attempting an illegal task lifecycle state transition."""
    def __init__(self, task_id: str, current_state: str, target_state: str) -> None:
        super().__init__(
            f"Invalid task transition for '{task_id}': {current_state} -> {target_state}",
            error_code="INVALID_TASK_TRANSITION",
            details={"task_id": task_id, "current_state": current_state, "target_state": target_state},
        )


class TaskRejectedError(RuntimeEngineException):
    """Raised when a task submission is rejected by admission control or policy."""
    def __init__(self, reason: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(f"Task rejected: {reason}", error_code="TASK_REJECTED", details=details)


class ResourceAdmissionError(RuntimeEngineException):
    """Raised when resource capacity is insufficient to admit work."""
    def __init__(self, reason: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(f"Resource admission denied: {reason}", error_code="RESOURCE_ADMISSION_DENIED", details=details)


class FencingRejectedError(RuntimeEngineException):
    """Raised when an operation is rejected due to a stale fencing epoch."""
    def __init__(self, active_epoch: int, attempted_epoch: int, entity_id: str) -> None:
        super().__init__(
            f"Fencing epoch rejected for '{entity_id}': attempted epoch {attempted_epoch} < active epoch {active_epoch}",
            error_code="FENCING_REJECTED",
            details={"active_epoch": active_epoch, "attempted_epoch": attempted_epoch, "entity_id": entity_id},
        )


class LeaseExpiredError(RuntimeEngineException):
    """Raised when attempting an operation under an expired execution lease."""
    def __init__(self, lease_id: str) -> None:
        super().__init__(f"Execution lease '{lease_id}' has expired.", error_code="LEASE_EXPIRED", details={"lease_id": lease_id})


class TaskExecutionError(RuntimeEngineException):
    """Raised when task execution fails unhandled."""
    def __init__(self, task_id: str, cause: str, details: Optional[Mapping[str, Any]] = None) -> None:
        d = dict(details or {})
        d["task_id"] = task_id
        super().__init__(f"Execution failed for task '{task_id}': {cause}", error_code="TASK_EXECUTION_FAILED", details=d)


class PauseUnsupportedError(RuntimeEngineException):
    """Raised when pause is requested for a task that does not support pause."""
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task '{task_id}' does not support physical pause.", error_code="PAUSE_UNSUPPORTED", details={"task_id": task_id})


class CancellationUnsupportedError(RuntimeEngineException):
    """Raised when cancellation is requested for an un-cancellable task."""
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task '{task_id}' does not support cancellation.", error_code="CANCELLATION_UNSUPPORTED", details={"task_id": task_id})
