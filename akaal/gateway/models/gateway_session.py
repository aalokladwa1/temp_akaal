"""
NexusForge — Gateway Session Model
=====================================
Tracks the complete lifecycle of a single upload through the Input Gateway.

Every field is populated progressively as the upload passes through each
pipeline stage. The session is the authoritative record of what happened
to an upload — from receipt to Manager handoff (or rejection).

Design:
  - Created at first byte received
  - Updated at each stage transition
  - Never deleted during processing
  - Serialisable to dict for audit / logging

GatewayStatus state machine:
  PENDING → VALIDATING → DETECTED → FORWARDED
                       ↘          ↘
                       REJECTED   FAILED
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.models.enums import FileFormat, GatewayStatus, SystemType


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class GatewaySession:
    """
    Lifecycle record for a single Input Gateway upload session.

    Every upload creates exactly one GatewaySession. The session tracks
    all metadata, detection results, and status transitions.
    It is the single source of truth for what happened to a given upload.
    """

    # ----------------------------------------------------------------
    # Identity — immutable after creation
    # ----------------------------------------------------------------
    session_id: str = field(default_factory=_new_id)
    migration_id: str = field(default_factory=_new_id)
    upload_timestamp: str = field(default_factory=_utc_now)

    # ----------------------------------------------------------------
    # File metadata — populated by UploadController
    # ----------------------------------------------------------------
    original_filename: str = ""
    sanitized_filename: str = ""
    file_path: str = ""           # Path to staged (temp) copy
    file_size_bytes: int = 0
    file_extension: str = ""      # e.g. ".sql", ".json", ".csv"
    file_format: Optional[FileFormat] = None

    # ----------------------------------------------------------------
    # Detection results — populated by FormatDetectionEngine
    # ----------------------------------------------------------------
    detected_db_type: Optional[SystemType] = None
    detection_confidence: float = 0.0
    detection_evidence: List[str] = field(default_factory=list)

    # ----------------------------------------------------------------
    # Parse metadata — populated by parser layer
    # ----------------------------------------------------------------
    table_count: int = 0
    estimated_row_count: int = 0
    schema_hints: Dict[str, Any] = field(default_factory=dict)
    parse_warnings: List[str] = field(default_factory=list)

    # ----------------------------------------------------------------
    # Status tracking
    # ----------------------------------------------------------------
    status: GatewayStatus = GatewayStatus.PENDING
    status_history: List[Dict[str, str]] = field(default_factory=list)

    # Progress is a free-form dict so callers can introspect any stage
    progress: Dict[str, Any] = field(default_factory=dict)

    # ----------------------------------------------------------------
    # Request context — populated from GatewayRequest
    # ----------------------------------------------------------------
    requested_by: str = "unknown"
    project_name: str = ""
    caller_db_hint: Optional[SystemType] = None   # Optional hint from caller

    # ----------------------------------------------------------------
    # Forwarding results — populated by ManagerBridge
    # ----------------------------------------------------------------
    project_id: Optional[str] = None
    manager_request_sent_at: Optional[str] = None

    # ----------------------------------------------------------------
    # Error / warning tracking
    # ----------------------------------------------------------------
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # ----------------------------------------------------------------
    # Internal timestamps
    # ----------------------------------------------------------------
    validation_started_at: Optional[str] = None
    validation_completed_at: Optional[str] = None
    detection_completed_at: Optional[str] = None
    parse_completed_at: Optional[str] = None

    # ----------------------------------------------------------------
    # Lifecycle transitions
    # ----------------------------------------------------------------

    def transition_to(self, new_status: GatewayStatus, reason: str = "") -> None:
        """
        Move session to a new status.
        Every transition is recorded in status_history for full traceability.
        """
        previous = self.status
        self.status = new_status
        self.status_history.append({
            "from": previous.value,
            "to": new_status.value,
            "timestamp": _utc_now(),
            "reason": reason,
        })

    def mark_rejected(self, error_code: str, message: str) -> None:
        """Convenience: record rejection with structured error."""
        self.error_code = error_code
        self.error_message = message
        self.transition_to(GatewayStatus.REJECTED, reason=f"{error_code}: {message}")

    def mark_failed(self, error_code: str, message: str) -> None:
        """Convenience: record internal failure with structured error."""
        self.error_code = error_code
        self.error_message = message
        self.transition_to(GatewayStatus.FAILED, reason=f"{error_code}: {message}")

    def add_warning(self, message: str) -> None:
        """Append a non-fatal warning."""
        self.warnings.append(message)

    def set_progress(self, stage: str, value: Any) -> None:
        """Update the progress map for a named stage."""
        self.progress[stage] = value

    def is_terminal(self) -> bool:
        """Return True if the session is in a non-resumable state."""
        return self.status in (
            GatewayStatus.FORWARDED,
            GatewayStatus.REJECTED,
            GatewayStatus.FAILED,
        )

    # ----------------------------------------------------------------
    # Serialisation
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise session to a plain dict for logging/audit."""
        return {
            "session_id": self.session_id,
            "migration_id": self.migration_id,
            "upload_timestamp": self.upload_timestamp,
            "original_filename": self.original_filename,
            "sanitized_filename": self.sanitized_filename,
            "file_size_bytes": self.file_size_bytes,
            "file_extension": self.file_extension,
            "file_format": self.file_format.value if self.file_format else None,
            "detected_db_type": self.detected_db_type.value if self.detected_db_type else None,
            "detection_confidence": self.detection_confidence,
            "detection_evidence": self.detection_evidence,
            "table_count": self.table_count,
            "estimated_row_count": self.estimated_row_count,
            "schema_hints": self.schema_hints,
            "parse_warnings": self.parse_warnings,
            "status": self.status.value,
            "status_history": self.status_history,
            "progress": self.progress,
            "requested_by": self.requested_by,
            "project_name": self.project_name,
            "caller_db_hint": self.caller_db_hint.value if self.caller_db_hint else None,
            "project_id": self.project_id,
            "manager_request_sent_at": self.manager_request_sent_at,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "warnings": self.warnings,
            "validation_started_at": self.validation_started_at,
            "validation_completed_at": self.validation_completed_at,
            "detection_completed_at": self.detection_completed_at,
            "parse_completed_at": self.parse_completed_at,
        }

    def __repr__(self) -> str:
        return (
            f"GatewaySession("
            f"session_id={self.session_id[:8]}..., "
            f"file={self.original_filename!r}, "
            f"status={self.status.value}, "
            f"db={self.detected_db_type})"
        )
