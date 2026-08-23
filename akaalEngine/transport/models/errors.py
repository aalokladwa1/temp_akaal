"""
akaalEngine.transport.models.errors
====================================
Typed exception hierarchy for Authority #9 Transport.
"""

from typing import Any, Mapping, Optional


class TransportError(Exception):
    """Base exception for Authority #9 Transport."""
    def __init__(self, message: str, error_code: str = "TRANSPORT_ERROR", details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(f"[{error_code}] {message}")
        self.message = message
        self.error_code = error_code
        self.details = dict(details or {})


class TransportReadError(TransportError):
    """Raised when reading from source fails."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="TRANSPORT_READ_ERROR", details=details)


class TransportWriteError(TransportError):
    """Raised when writing to target fails."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="TRANSPORT_WRITE_ERROR", details=details)


class TransportTimeoutError(TransportError):
    """Raised when transport operation times out."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="TRANSPORT_TIMEOUT")


class TransportRetryExhaustedError(TransportError):
    """Raised when maximum retry attempts are exhausted."""
    def __init__(self, attempts: int, last_error: str) -> None:
        super().__init__(f"Retry exhausted after {attempts} attempts. Last error: {last_error}", error_code="RETRY_EXHAUSTED", details={"attempts": attempts, "last_error": last_error})


class TransportCancelledError(TransportError):
    """Raised when transport operation is cancelled."""
    def __init__(self, reason: str = "Operation cancelled") -> None:
        super().__init__(f"Transport operation cancelled: {reason}", error_code="TRANSPORT_CANCELLED")


class TransportFencingError(TransportError):
    """Raised when fencing token validation fails."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="TRANSPORT_FENCING_ERROR")


class TransportCheckpointIdentityError(TransportError):
    """Raised when checkpoint identity mismatch occurs."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CHECKPOINT_IDENTITY_MISMATCH")


class TransportCheckpointStaleError(TransportError):
    """Raised when checkpoint generation is stale."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CHECKPOINT_STALE")


class AmbiguousCommitError(TransportError):
    """Raised when transaction commit outcome cannot be authoritatively proven (FAIL CLOSED)."""
    def __init__(self, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message, error_code="AMBIGUOUS_COMMIT_OUTCOME", details=details)


class TransportChecksumScopeError(TransportError):
    """Raised when comparing checksums across mismatched scopes."""
    def __init__(self, expected_scope: str, actual_scope: str) -> None:
        super().__init__(f"Checksum scope mismatch: expected '{expected_scope}', got '{actual_scope}'", error_code="CHECKSUM_SCOPE_MISMATCH")


class TransportCapabilityError(TransportError):
    """Raised when requested transport capability or codec is unsupported."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="CAPABILITY_UNSUPPORTED")


class BandwidthLimitError(TransportError):
    """Raised when bandwidth governor fails."""
    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="BANDWIDTH_LIMIT_ERROR")
