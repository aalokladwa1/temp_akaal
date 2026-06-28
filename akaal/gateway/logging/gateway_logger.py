"""
NexusForge — Gateway Structured Logger
=========================================
Provides structured, consistent logging for every event that occurs
inside the Input Gateway pipeline.

Every log record includes:
  - timestamp (UTC ISO-8601)
  - event      (event type string)
  - session_id (always present for traceability)
  - level      (DEBUG / INFO / WARNING / ERROR)
  - details    (dict of event-specific fields)

The GatewayLogger wraps Python's standard logging module.
It does NOT write to disk itself — that is handled by the configured
logging handlers. This ensures the Gateway is decoupled from storage.

Usage:
    logger = GatewayLogger()
    logger.log_upload_started(session)
    logger.log_validation_success(session)
    logger.log_db_detected(session, SystemType.MYSQL, 0.92)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from akaal.core.models.enums import GatewayStatus, SystemType
from akaal.gateway.models.gateway_session import GatewaySession


_logger = logging.getLogger("nexusforge.gateway")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GatewayLogger:
    """
    Structured event logger for all Input Gateway pipeline stages.

    All methods follow the same pattern:
        - Build a structured log record (dict)
        - Emit via Python logging at the appropriate level
        - Attach session_id to every record for traceability
    """

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _emit(
        self,
        level: int,
        event: str,
        session_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Build and emit a structured log record."""
        record = {
            "timestamp": _utc_now(),
            "event": event,
            "session_id": session_id,
            "level": logging.getLevelName(level),
            "details": details or {},
        }
        # Use json.dumps for machine-parsable structured output
        _logger.log(level, json.dumps(record, default=str))

    # ----------------------------------------------------------------
    # Upload lifecycle events
    # ----------------------------------------------------------------

    def log_upload_started(self, session: GatewaySession) -> None:
        """Log when an upload is first received by the Gateway."""
        self._emit(
            logging.INFO,
            "UPLOAD_STARTED",
            session.session_id,
            {
                "original_filename": session.original_filename,
                "requested_by": session.requested_by,
                "migration_id": session.migration_id,
            },
        )

    def log_upload_completed(self, session: GatewaySession) -> None:
        """Log when an upload has been staged successfully."""
        self._emit(
            logging.INFO,
            "UPLOAD_COMPLETED",
            session.session_id,
            {
                "sanitized_filename": session.sanitized_filename,
                "file_size_bytes": session.file_size_bytes,
                "file_extension": session.file_extension,
                "staged_path": session.file_path,
            },
        )

    # ----------------------------------------------------------------
    # Validation events
    # ----------------------------------------------------------------

    def log_validation_success(self, session: GatewaySession) -> None:
        """Log when file validation passes all checks."""
        self._emit(
            logging.INFO,
            "VALIDATION_SUCCESS",
            session.session_id,
            {
                "file_size_bytes": session.file_size_bytes,
                "file_extension": session.file_extension,
                "sanitized_filename": session.sanitized_filename,
            },
        )

    def log_validation_failure(self, session: GatewaySession, reason: str) -> None:
        """Log when file validation fails (structured rejection)."""
        self._emit(
            logging.WARNING,
            "VALIDATION_FAILURE",
            session.session_id,
            {
                "reason": reason,
                "error_code": session.error_code,
                "original_filename": session.original_filename,
            },
        )

    # ----------------------------------------------------------------
    # Detection events
    # ----------------------------------------------------------------

    def log_db_detected(
        self,
        session: GatewaySession,
        db_type: Optional[SystemType],
        confidence: float,
    ) -> None:
        """Log database vendor detection result."""
        level = logging.INFO if db_type is not None else logging.WARNING
        self._emit(
            level,
            "DB_DETECTED",
            session.session_id,
            {
                "detected_db_type": db_type.value if db_type else None,
                "confidence": round(confidence, 4),
                "evidence": session.detection_evidence,
            },
        )

    def log_confidence_too_low(self, session: GatewaySession, confidence: float, threshold: float) -> None:
        """Log when confidence is below threshold and user action is required."""
        self._emit(
            logging.WARNING,
            "CONFIDENCE_TOO_LOW",
            session.session_id,
            {
                "confidence": round(confidence, 4),
                "threshold": threshold,
                "message": "User must specify the database type manually.",
            },
        )

    # ----------------------------------------------------------------
    # Manager forwarding events
    # ----------------------------------------------------------------

    def log_manager_request_sent(self, session: GatewaySession, project_id: str) -> None:
        """Log when the validated request is forwarded to the Manager Agent."""
        self._emit(
            logging.INFO,
            "MANAGER_REQUEST_SENT",
            session.session_id,
            {
                "project_id": project_id,
                "migration_id": session.migration_id,
                "detected_db_type": session.detected_db_type.value if session.detected_db_type else None,
            },
        )

    # ----------------------------------------------------------------
    # Error / warning events
    # ----------------------------------------------------------------

    def log_error(
        self,
        session: GatewaySession,
        error_code: str,
        message: str,
        exc: Optional[Exception] = None,
    ) -> None:
        """Log a structured error event."""
        details: Dict[str, Any] = {
            "error_code": error_code,
            "message": message,
            "original_filename": session.original_filename,
        }
        if exc is not None:
            details["exception_type"] = type(exc).__name__
            details["exception_message"] = str(exc)
        self._emit(logging.ERROR, "GATEWAY_ERROR", session.session_id, details)

    def log_warning(self, session: GatewaySession, message: str) -> None:
        """Log a non-fatal warning."""
        self._emit(
            logging.WARNING,
            "GATEWAY_WARNING",
            session.session_id,
            {"message": message},
        )

    def log_stage_progress(self, session: GatewaySession, stage: str, detail: Any = None) -> None:
        """Log a named stage progress update (debug level)."""
        self._emit(
            logging.DEBUG,
            f"STAGE_{stage.upper()}",
            session.session_id,
            {"stage": stage, "detail": detail},
        )
