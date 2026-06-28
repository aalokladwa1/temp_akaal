"""
NexusForge — Upload Controller
==================================
Orchestrates the complete upload processing pipeline:

  1. Stage file securely (SecureFileStorage)
  2. Validate file (FileValidationEngine)
  3. Detect format + database vendor (FormatDetectionEngine)
  4. Select and run the appropriate parser
  5. Populate and return the GatewaySession

The UploadController is the pipeline coordinator. It delegates each
step to a dedicated component and never implements the logic itself
(Single Responsibility Principle).

Error handling:
  - Any step failure marks the session as REJECTED or FAILED
  - Storage is ALWAYS released in a finally block
  - Exceptions are caught and converted to structured session state
  - The caller always receives a populated GatewaySession (never an exception)
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from akaal.core.models.enums import FileFormat, GatewayStatus, SystemType
from akaal.gateway.detection.format_detection_engine import FormatDetectionEngine
from akaal.gateway.logging.gateway_logger import GatewayLogger
from akaal.gateway.models.gateway_request import GatewayRequest
from akaal.gateway.models.gateway_response import GatewayErrorCode
from akaal.gateway.models.gateway_session import GatewaySession
from akaal.gateway.parsers.base_parser import AbstractParser, ParseResult
from akaal.gateway.parsers.csv_parser import CsvParser
from akaal.gateway.parsers.json_parser import JsonParser
from akaal.gateway.parsers.sql_parser import SqlParser
from akaal.gateway.upload.storage import SecureFileStorage, StorageError
from akaal.gateway.validation.validation_engine import FileValidationEngine


logger = logging.getLogger("nexusforge.gateway.upload_controller")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UploadController:
    """
    Orchestrates the upload pipeline: stage → validate → detect → parse.

    Returns a fully-populated GatewaySession after all pipeline stages.
    Session status reflects the outcome:
      - DETECTED:  All stages passed; ready to be forwarded to Manager
      - REJECTED:  A validation or detection check failed
      - FAILED:    An unexpected internal error occurred

    Usage:
        controller = UploadController()
        session = controller.handle_upload(request)
    """

    def __init__(
        self,
        storage: Optional[SecureFileStorage] = None,
        validation_engine: Optional[FileValidationEngine] = None,
        detection_engine: Optional[FormatDetectionEngine] = None,
        gateway_logger: Optional[GatewayLogger] = None,
        parsers: Optional[List[AbstractParser]] = None,
    ) -> None:
        self._storage = storage or SecureFileStorage()
        self._validator = validation_engine or FileValidationEngine()
        self._detector = detection_engine or FormatDetectionEngine()
        self._log = gateway_logger or GatewayLogger()

        # Parser registry — ordered; first matching parser wins
        self._parsers: List[AbstractParser] = parsers or [
            SqlParser(),
            JsonParser(),
            CsvParser(),
        ]

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def handle_upload(self, request: GatewayRequest) -> GatewaySession:
        """
        Run the full upload pipeline for a single request.

        Parameters
        ----------
        request : GatewayRequest
            Validated caller request.

        Returns
        -------
        GatewaySession
            Always returned; never raises to the caller.
            Check session.status for the outcome.
        """
        import os
        original_filename = os.path.basename(request.file_path)

        # --- Create session ---
        session = GatewaySession(
            original_filename=original_filename,
            requested_by=request.requested_by,
            project_name=request.project_name or original_filename,
            caller_db_hint=request.target_db_type,
        )
        session.transition_to(GatewayStatus.PENDING, "Upload received")
        self._log.log_upload_started(session)

        staged_path: Optional[str] = None

        try:
            # ── Stage 1: Secure file staging ──────────────────────────
            session.set_progress("staging", "in_progress")
            staged_path = self._stage_file(session, request)
            if session.is_terminal():
                return session  # Staging failed

            session.set_progress("staging", "completed")
            self._log.log_upload_completed(session)

            # ── Stage 2: File validation ───────────────────────────────
            session.transition_to(GatewayStatus.VALIDATING, "Starting file validation")
            session.validation_started_at = _utc_now()
            session.set_progress("validation", "in_progress")

            valid = self._validate_file(session, staged_path)
            if not valid:
                return session  # Validation failed (session already marked REJECTED)

            session.validation_completed_at = _utc_now()
            session.set_progress("validation", "passed")
            self._log.log_validation_success(session)

            # ── Stage 3: Format + vendor detection ────────────────────
            session.set_progress("detection", "in_progress")
            detected = self._detect_format(session, staged_path)
            if not detected:
                return session  # Detection failed or low confidence

            session.detection_completed_at = _utc_now()
            session.set_progress("detection", "completed")
            self._log.log_db_detected(session, session.detected_db_type, session.detection_confidence)

            # ── Stage 4: Parse metadata ───────────────────────────────
            session.set_progress("parsing", "in_progress")
            self._parse_metadata(session, staged_path)
            session.parse_completed_at = _utc_now()
            session.set_progress("parsing", "completed")

            # ── Done: mark as DETECTED and ready for Manager ───────────
            session.transition_to(GatewayStatus.DETECTED, "File processed; ready for Manager")
            logger.info(
                "[UploadController] Session %s completed pipeline. db=%s confidence=%.2f",
                session.session_id[:8],
                session.detected_db_type,
                session.detection_confidence,
            )

        except Exception as exc:
            logger.error(
                "[UploadController] Unexpected error in session %s: %s",
                session.session_id[:8], exc, exc_info=True,
            )
            self._log.log_error(session, GatewayErrorCode.INTERNAL_ERROR, str(exc), exc)
            session.mark_failed(GatewayErrorCode.INTERNAL_ERROR, str(exc))

        finally:
            # Always release staged file (success or failure)
            if staged_path is not None:
                self._storage.release(session.session_id)

        return session

    # ----------------------------------------------------------------
    # Pipeline stage implementations
    # ----------------------------------------------------------------

    def _stage_file(self, session: GatewaySession, request: GatewayRequest) -> Optional[str]:
        """Stage the uploaded file. Returns staged_path or None on failure."""
        try:
            staged_path = self._storage.stage(
                session_id=session.session_id,
                source_path=request.file_path,
                sanitized_filename=session.original_filename,
            )
            session.file_path = staged_path
            session.file_size_bytes = self._get_file_size(staged_path)
            return staged_path
        except StorageError as exc:
            self._log.log_error(session, GatewayErrorCode.STORAGE_FAILURE, str(exc), exc)
            session.mark_rejected(GatewayErrorCode.STORAGE_FAILURE, str(exc))
            return None
        except Exception as exc:
            self._log.log_error(session, GatewayErrorCode.INTERNAL_ERROR, str(exc), exc)
            session.mark_failed(GatewayErrorCode.INTERNAL_ERROR, str(exc))
            return None

    def _validate_file(self, session: GatewaySession, staged_path: str) -> bool:
        """Run FileValidationEngine. Returns True if valid, False on rejection."""
        result = self._validator.validate(
            file_path=staged_path,
            original_filename=session.original_filename,
        )

        if not result.success:
            self._log.log_validation_failure(session, result.error_message or "Unknown")
            session.mark_rejected(
                result.error_code or GatewayErrorCode.INTERNAL_ERROR,
                result.error_message or "Validation failed",
            )
            return False

        # Populate session with validated metadata
        session.sanitized_filename = result.sanitized_filename
        session.file_size_bytes = result.file_size_bytes
        session.file_extension = result.file_extension

        for warning in result.warnings:
            session.add_warning(warning)

        return True

    def _detect_format(self, session: GatewaySession, staged_path: str) -> bool:
        """
        Run FormatDetectionEngine.

        Returns True if detection is confident enough to proceed.
        Returns False if user action is required or detection fails.
        """
        detection = self._detector.detect(
            file_path=staged_path,
            extension=session.file_extension,
        )

        # Always store detection results
        session.file_format = detection.file_format
        session.detected_db_type = detection.db_type
        session.detection_confidence = detection.confidence
        session.detection_evidence = detection.evidence

        # If caller provided a DB type hint and confidence is low, accept the hint
        if detection.requires_user_input and session.caller_db_hint is not None:
            session.detected_db_type = session.caller_db_hint
            session.detection_confidence = 1.0  # Caller-confirmed
            session.add_warning(
                f"Auto-detection confidence was low ({detection.confidence:.2f}). "
                f"Using caller-provided hint: {session.caller_db_hint.value}"
            )
            logger.info(
                "[UploadController] Used caller hint %s for session %s",
                session.caller_db_hint.value, session.session_id[:8],
            )
            return True

        if detection.requires_user_input:
            self._log.log_confidence_too_low(
                session,
                detection.confidence,
                self._detector._threshold,
            )
            session.mark_rejected(
                GatewayErrorCode.CONFIDENCE_TOO_LOW,
                (
                    f"Database vendor could not be confidently detected "
                    f"(confidence={detection.confidence:.2f}). "
                    "Please re-submit with target_db_type specified."
                ),
            )
            return False

        return True

    def _parse_metadata(self, session: GatewaySession, staged_path: str) -> None:
        """
        Find and run the appropriate parser.
        Failures here are non-fatal — we add warnings but don't reject.
        """
        parser = self._find_parser(session.file_extension)
        if parser is None:
            session.add_warning(
                f"No parser available for extension {session.file_extension!r}. "
                "Schema metadata will not be available."
            )
            return

        try:
            result: ParseResult = parser.parse(staged_path)
        except Exception as exc:
            session.add_warning(f"Parser raised unexpected error: {exc}")
            logger.warning(
                "[UploadController] Parser %s raised for session %s: %s",
                parser.name, session.session_id[:8], exc,
            )
            return

        if result.success:
            session.table_count = result.table_count
            session.estimated_row_count = result.estimated_row_count
            session.schema_hints = result.schema_hints
            for w in result.warnings:
                session.add_warning(w)
        else:
            session.add_warning(
                f"Parser could not extract metadata: {result.error_message}"
            )

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _find_parser(self, extension: str) -> Optional[AbstractParser]:
        """Return the first registered parser that handles the extension."""
        for parser in self._parsers:
            if parser.can_parse(extension):
                return parser
        return None

    @staticmethod
    def _get_file_size(file_path: str) -> int:
        """Return file size in bytes; 0 on error."""
        import os
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
