"""
akaalEngine.cdc.models.errors
==============================
Typed exception hierarchy for Authority #10 CDC / Incremental Replication.
"""

from typing import Any, Mapping, Optional


class CDCError(Exception):
    """Base exception for Authority #10 CDC."""
    def __init__(self, message: str, error_code: str = "CDC_ERROR", details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(f"[{error_code}] {message}")
        self.message = message
        self.error_code = error_code
        self.details = dict(details or {})


class CDCCapabilityError(CDCError):
    """Raised when requested CDC capability is unsupported or unavailable."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CDC_CAPABILITY_UNSUPPORTED")


class CDCPermissionError(CDCError):
    """Raised when provider prerequisite or permission preflight check fails."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="CDC_PREREQUISITE_FAILED", details=details)


class CDCPositionError(CDCError):
    """Raised when source position is malformed or invalid."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CDC_POSITION_MALFORMED")


class CDCCheckpointIdentityError(CDCError):
    """Raised when CDC checkpoint identity or resource version is mismatched."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CDC_CHECKPOINT_IDENTITY_MISMATCH")


class CDCSourceRetentionError(CDCError):
    """Raised when source WAL / binlog / archive retention is exhausted or lost."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CDC_SOURCE_RETENTION_LOST")


class CDCTransactionError(CDCError):
    """Raised when transaction reconstruction or commit ordering fails."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CDC_TRANSACTION_ERROR")


class CDCApplyError(CDCError):
    """Raised when CDC event application fails on target."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="CDC_APPLY_ERROR", details=details)


class CDCSchemaChangeError(CDCError):
    """Raised when an unhandled or incompatible DDL event is encountered."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CDC_SCHEMA_CHANGE_INCOMPATIBLE")


class CDCCutoverNotReadyError(CDCError):
    """Raised when cutover is attempted before TECHNICAL_CUTOVER_READY criteria are proven."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="CUTOVER_NOT_READY", details=details)


class CDCFencingError(CDCError):
    """Raised when fencing token validation fails during CDC operations."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CDC_FENCING_ERROR")


class CDCCancelledError(CDCError):
    """Raised when CDC capture or apply operation is cancelled."""
    def __init__(self, reason: str = "Operation cancelled") -> None:
        super().__init__(f"CDC operation cancelled: {reason}", error_code="CDC_CANCELLED")
