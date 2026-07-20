"""Standardized Exception Hierarchy for AKAAL Workflow Platform."""

class WorkflowException(Exception):
    """Base exception for all workflow platform errors."""
    pass


class InvalidStateTransitionException(WorkflowException):
    """Raised when an invalid state machine transition is attempted."""
    def __init__(self, current_state: str, target_state: str, reason: str = "") -> None:
        message = f"Invalid transition from state '{current_state}' to '{target_state}'."
        if reason:
            message += f" Reason: {reason}"
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state


class ChecksumMismatchException(WorkflowException):
    """Raised when payload checksum validation fails."""
    def __init__(self, expected: str, actual: str, payload_type: str = "Payload") -> None:
        super().__init__(
            f"{payload_type} checksum mismatch! Expected: {expected}, Got: {actual}"
        )
        self.expected = expected
        self.actual = actual


class StepExecutionException(WorkflowException):
    """Raised when a step execution fails."""
    def __init__(self, step_id: str, message: str, cause: Exception | None = None) -> None:
        super().__init__(f"Step '{step_id}' execution failed: {message}")
        self.step_id = step_id
        self.cause = cause


class StepTimeoutException(StepExecutionException):
    """Raised when a step exceeds its configured timeout duration."""
    def __init__(self, step_id: str, timeout_seconds: float) -> None:
        super().__init__(step_id, f"Exceeded timeout limit of {timeout_seconds}s")
        self.timeout_seconds = timeout_seconds


class StepRetryExhaustedException(StepExecutionException):
    """Raised when all retry attempts for a step have failed."""
    def __init__(self, step_id: str, attempts: int, last_error: Exception | None) -> None:
        super().__init__(step_id, f"Exhausted all {attempts} retry attempts", cause=last_error)
        self.attempts = attempts
        self.last_error = last_error


class PreconditionFailedException(StepExecutionException):
    """Raised when a step precondition check fails prior to execution."""
    def __init__(self, step_id: str, reason: str) -> None:
        super().__init__(step_id, f"Precondition failed: {reason}")
        self.reason = reason


class PostconditionFailedException(StepExecutionException):
    """Raised when a step postcondition check fails after execution."""
    def __init__(self, step_id: str, reason: str) -> None:
        super().__init__(step_id, f"Postcondition failed: {reason}")
        self.reason = reason


class ManifestValidationException(WorkflowException):
    """Raised when structural manifest validation fails."""
    def __init__(self, errors: list[str]) -> None:
        super().__init__(f"Manifest structural validation failed: {'; '.join(errors)}")
        self.errors = errors


class StepNotFoundException(WorkflowException):
    """Raised when a step cannot be resolved in the step registry."""
    def __init__(self, step_type: str) -> None:
        super().__init__(f"Step type '{step_type}' not registered in WorkflowStepRegistry.")
        self.step_type = step_type


class CheckpointException(WorkflowException):
    """Base exception for checkpoint operations."""
    pass


class CheckpointNotFoundException(CheckpointException):
    """Raised when a requested checkpoint does not exist."""
    def __init__(self, checkpoint_id: str) -> None:
        super().__init__(f"Checkpoint '{checkpoint_id}' not found.")
        self.checkpoint_id = checkpoint_id


class CheckpointCorruptException(CheckpointException):
    """Raised when a loaded checkpoint fails integrity or checksum checks."""
    def __init__(self, checkpoint_id: str, reason: str) -> None:
        super().__init__(f"Checkpoint '{checkpoint_id}' is corrupt: {reason}")
        self.checkpoint_id = checkpoint_id


class LockAcquisitionException(WorkflowException):
    """Raised when a workflow lock cannot be acquired."""
    def __init__(self, workflow_id: str, reason: str = "") -> None:
        message = f"Failed to acquire workflow lock for workflow '{workflow_id}'."
        if reason:
            message += f" Reason: {reason}"
        super().__init__(message)
        self.workflow_id = workflow_id
