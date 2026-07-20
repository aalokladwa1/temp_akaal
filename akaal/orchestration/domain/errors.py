"""
Enterprise Workflow Exception Hierarchy.
Avoids primitive or generic exception handling across orchestration components.
"""

from typing import Optional, Any


class WorkflowError(Exception):
    """Base exception class for all orchestration workflow errors."""
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidStateTransitionError(WorkflowError):
    """Raised when an illegal workflow state transition is attempted."""
    def __init__(self, from_state: str, to_state: str, reason: str = "") -> None:
        msg = f"Invalid state transition attempted: {from_state} -> {to_state}."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg, {"from_state": from_state, "to_state": to_state, "reason": reason})


class RecoveryError(WorkflowError):
    """Raised when deterministic session or checkpoint recovery fails validation."""
    pass


class ConfigurationError(WorkflowError):
    """Raised when configuration validation, versioning, or checksum verification fails."""
    pass


class SessionExpiredError(WorkflowError):
    """Raised when accessing or renewing an expired session lease."""
    pass


class CheckpointError(WorkflowError):
    """Raised when checkpoint creation, corruption, or checksum validation fails."""
    pass


class RepositoryError(WorkflowError):
    """Raised when repository query, save, update, or deletion operations fail."""
    pass


class WorkflowExecutionError(WorkflowError):
    """Raised when a workflow step or engine execution fails."""
    pass
