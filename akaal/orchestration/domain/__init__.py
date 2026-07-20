"""
Akaal Orchestration Shared Domain Package.
Contains strongly typed identifiers, domain enums, value objects, and exception hierarchy.
"""

from akaal.orchestration.domain.identifiers import (
    JobId,
    WorkflowId,
    SessionId,
    ConfigurationId,
)
from akaal.orchestration.domain.types import (
    Version,
    Checksum,
    AuditMetadata,
    EngineState,
    WorkflowStepName,
)
from akaal.orchestration.domain.errors import (
    WorkflowError,
    InvalidStateTransitionError,
    RecoveryError,
    ConfigurationError,
    SessionExpiredError,
    CheckpointError,
    RepositoryError,
    WorkflowExecutionError,
)

__all__ = [
    "JobId",
    "WorkflowId",
    "SessionId",
    "ConfigurationId",
    "Version",
    "Checksum",
    "AuditMetadata",
    "EngineState",
    "WorkflowStepName",
    "WorkflowError",
    "InvalidStateTransitionError",
    "RecoveryError",
    "ConfigurationError",
    "SessionExpiredError",
    "CheckpointError",
    "RepositoryError",
    "WorkflowExecutionError",
]
