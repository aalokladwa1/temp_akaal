"""
NexusForge — Gateway Response Model
======================================
Caller-facing output contract for the Input Gateway.

Every call to InputGateway.process_upload() returns a GatewayResponse —
never raises an exception to the caller. Failures are embedded as
structured GatewayError objects.

This ensures the Gateway is always a stable boundary that
callers can safely consume without try/except.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from akaal.core.models.enums import GatewayStatus, SystemType


# ---------------------------------------------------------------------------
# Error Codes (string constants to avoid magic strings)
# ---------------------------------------------------------------------------

class GatewayErrorCode:
    """Enumeration of all possible Gateway error codes."""
    # File / upload errors
    FILE_NOT_FOUND        = "FILE_NOT_FOUND"
    FILE_NOT_READABLE     = "FILE_NOT_READABLE"
    FILE_EMPTY            = "FILE_EMPTY"
    FILE_TOO_LARGE        = "FILE_TOO_LARGE"
    FILE_CORRUPTED        = "FILE_CORRUPTED"
    FILE_INCOMPLETE       = "FILE_INCOMPLETE"

    # Filename / path security
    UNSAFE_FILENAME       = "UNSAFE_FILENAME"
    PATH_TRAVERSAL        = "PATH_TRAVERSAL"

    # Format errors
    UNSUPPORTED_FORMAT    = "UNSUPPORTED_FORMAT"
    PARSE_FAILED          = "PARSE_FAILED"

    # Detection errors
    CONFIDENCE_TOO_LOW    = "CONFIDENCE_TOO_LOW"   # User must confirm DB type
    DETECTION_FAILED      = "DETECTION_FAILED"

    # Storage errors
    STORAGE_FAILURE       = "STORAGE_FAILURE"

    # Manager communication errors
    MANAGER_UNAVAILABLE   = "MANAGER_UNAVAILABLE"
    MANAGER_REJECTED      = "MANAGER_REJECTED"
    MANAGER_TIMEOUT       = "MANAGER_TIMEOUT"

    # Internal errors
    INTERNAL_ERROR        = "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# GatewayError — structured error descriptor
# ---------------------------------------------------------------------------

@dataclass
class GatewayError:
    """
    Structured error returned when an upload cannot be processed.

    requires_user_action:
        True if the error can be resolved by the user providing additional
        information (e.g., manually selecting the database type when detection
        confidence is too low). False for system-level errors.
    """
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    requires_user_action: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "requires_user_action": self.requires_user_action,
        }

    def __repr__(self) -> str:
        return f"GatewayError(code={self.code!r}, requires_user_action={self.requires_user_action})"


# ---------------------------------------------------------------------------
# GatewayResponse — unified result envelope
# ---------------------------------------------------------------------------

@dataclass
class GatewayResponse:
    """
    The unified result envelope returned by InputGateway.process_upload().

    On success:
        success=True, project_id is set, error=None

    On failure:
        success=False, error is populated with a GatewayError

    On low-confidence detection:
        success=False, error.requires_user_action=True,
        error.code=CONFIDENCE_TOO_LOW,
        detected_db_type=None

    In all cases the session_id and migration_id are always populated
    so the upload is always traceable.
    """

    # Overall result
    success: bool

    # Always populated (traceability)
    session_id: str
    migration_id: str

    # Populated on success
    project_id: Optional[str] = None

    # Detection results (always populated when detection ran)
    detected_db_type: Optional[SystemType] = None
    detection_confidence: float = 0.0

    # Status and human-readable message
    status: GatewayStatus = GatewayStatus.PENDING
    message: str = ""

    # File metadata
    original_filename: str = ""
    file_size_bytes: int = 0
    table_count: int = 0
    estimated_row_count: int = 0

    # Warnings (non-fatal)
    warnings: List[str] = field(default_factory=list)

    # Error (populated on failure)
    error: Optional[GatewayError] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "session_id": self.session_id,
            "migration_id": self.migration_id,
            "project_id": self.project_id,
            "detected_db_type": self.detected_db_type.value if self.detected_db_type else None,
            "detection_confidence": self.detection_confidence,
            "status": self.status.value,
            "message": self.message,
            "original_filename": self.original_filename,
            "file_size_bytes": self.file_size_bytes,
            "table_count": self.table_count,
            "estimated_row_count": self.estimated_row_count,
            "warnings": self.warnings,
            "error": self.error.to_dict() if self.error else None,
        }

    def __repr__(self) -> str:
        if self.success:
            return (
                f"GatewayResponse(success=True, project_id={self.project_id!r}, "
                f"db={self.detected_db_type}, session={self.session_id[:8]}...)"
            )
        return (
            f"GatewayResponse(success=False, error={self.error!r}, "
            f"session={self.session_id[:8]}...)"
        )
