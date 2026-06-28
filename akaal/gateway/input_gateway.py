"""
NexusForge — Input Gateway Façade
======================================
The ONLY public entry point for all migration upload requests.

Architecture:
  InputGateway is a thin orchestration façade. It:
    1. Creates/delegates to UploadController for pipeline processing
    2. Delegates to ManagerBridge for Manager Agent communication
    3. Emits audit events via AuditLogger
    4. Returns a structured GatewayResponse — always

No agent (Scout, Validator, GB, Live Intel) is contacted by this class.
Only the ManagerBridge talks to the Manager Agent.

Usage:
    # Build dependencies
    manager_agent = ManagerAgent(...)
    audit_logger = AuditLogger(...)

    # Create gateway
    gateway = InputGateway(manager=manager_agent, audit_logger=audit_logger)

    # Process an upload
    request = GatewayRequest(
        file_path="/path/to/export.sql",
        requested_by="ops-team",
    )
    response = await gateway.process_upload(request)

    if response.success:
        print(f"Project created: {response.project_id}")
    else:
        print(f"Failed: {response.error.code} — {response.error.message}")
"""

import asyncio
import logging
from typing import Optional

from akaal.audit.audit_logger import AuditEventType, AuditLogger
from akaal.core.models.enums import GatewayStatus, MigrationStrategy
from akaal.gateway.communication.manager_bridge import ManagerBridge
from akaal.gateway.logging.gateway_logger import GatewayLogger
from akaal.gateway.models.gateway_request import GatewayRequest
from akaal.gateway.models.gateway_response import GatewayError, GatewayErrorCode, GatewayResponse
from akaal.gateway.models.gateway_session import GatewaySession
from akaal.gateway.upload.upload_controller import UploadController


logger = logging.getLogger("nexusforge.gateway")


class InputGateway:
    """
    The sole official entry point into the NexusForge migration pipeline.

    Every migration request MUST pass through this class.
    Direct access to any downstream agent is forbidden.

    Lifecycle of process_upload():
      1. GatewayRequest validation (fail-fast on missing required fields)
      2. UploadController.handle_upload() — file pipeline
      3. ManagerBridge.forward()           — Manager Agent handoff
      4. Return GatewayResponse

    The gateway NEVER raises exceptions to callers.
    All failures are encoded in GatewayResponse.error.
    """

    def __init__(
        self,
        manager: object,  # ManagerAgent — object to avoid circular import
        audit_logger: AuditLogger,
        upload_controller: Optional[UploadController] = None,
        manager_bridge: Optional[ManagerBridge] = None,
        gateway_logger: Optional[GatewayLogger] = None,
    ) -> None:
        """
        Parameters
        ----------
        manager : ManagerAgent
            The running Manager Agent instance.
        audit_logger : AuditLogger
            The system-wide audit logger.
        upload_controller : UploadController, optional
            Injected for testing. Defaults to a production-configured instance.
        manager_bridge : ManagerBridge, optional
            Injected for testing. Defaults to a production-configured instance.
        gateway_logger : GatewayLogger, optional
            Injected for testing. Defaults to a new GatewayLogger instance.
        """
        self._manager = manager
        self._audit = audit_logger
        self._gw_log = gateway_logger or GatewayLogger()
        self._controller = upload_controller or UploadController(gateway_logger=self._gw_log)
        self._bridge = manager_bridge or ManagerBridge(
            audit_logger=audit_logger,
            gateway_logger=self._gw_log,
        )

        logger.info("[InputGateway] Initialized.")

    # ----------------------------------------------------------------
    # Public API — the single entry point
    # ----------------------------------------------------------------

    async def process_upload(self, request: GatewayRequest) -> GatewayResponse:
        """
        Process a migration upload request end-to-end.

        This is the ONLY method callers should use. It runs the complete
        pipeline and returns a structured GatewayResponse.

        Parameters
        ----------
        request : GatewayRequest
            The upload request. File path must be accessible at call time.

        Returns
        -------
        GatewayResponse
            success=True  → project_id is populated, migration is queued
            success=False → error.code explains the failure
        """
        # ── Audit: upload received ─────────────────────────────────
        self._audit.log(
            event_type=AuditEventType.GATEWAY_UPLOAD_RECEIVED,
            actor="INPUT_GATEWAY",
            description=f"Upload request received from {request.requested_by!r}.",
            details={
                "file_path": request.file_path,
                "requested_by": request.requested_by,
                "migration_strategy": request.migration_strategy.value,
                "target_db_hint": request.target_db_type.value if request.target_db_type else None,
            },
        )

        logger.info(
            "[InputGateway] Upload request: file=%r requested_by=%r strategy=%s",
            request.file_path, request.requested_by, request.migration_strategy.value,
        )

        try:
            # ── Phase 1: Upload pipeline ───────────────────────────────
            session: GatewaySession = self._controller.handle_upload(request)

            # ── Phase 2: Audit validation result ───────────────────────
            if session.status == GatewayStatus.REJECTED:
                self._audit.log(
                    event_type=AuditEventType.GATEWAY_VALIDATION_FAILED,
                    actor="INPUT_GATEWAY",
                    description=f"Upload rejected: {session.error_code}",
                    details=session.to_dict(),
                )
                return self._build_rejection_response(session)

            if session.status == GatewayStatus.FAILED:
                self._audit.log(
                    event_type=AuditEventType.GATEWAY_REJECTED,
                    actor="INPUT_GATEWAY",
                    description=f"Upload failed internally: {session.error_code}",
                    details=session.to_dict(),
                )
                return self._build_rejection_response(session)

            # ── Audit: validation passed ────────────────────────────────
            self._audit.log(
                event_type=AuditEventType.GATEWAY_VALIDATION_PASSED,
                actor="INPUT_GATEWAY",
                description=f"File validation passed for '{session.original_filename}'.",
                details={
                    "session_id": session.session_id,
                    "file_size_bytes": session.file_size_bytes,
                    "detected_db_type": session.detected_db_type.value if session.detected_db_type else None,
                    "confidence": session.detection_confidence,
                },
            )

            # Audit: DB detected
            self._audit.log(
                event_type=AuditEventType.GATEWAY_DB_DETECTED,
                actor="INPUT_GATEWAY",
                description=f"Database detected: {session.detected_db_type}",
                details={
                    "session_id": session.session_id,
                    "db_type": session.detected_db_type.value if session.detected_db_type else None,
                    "confidence": session.detection_confidence,
                    "evidence": session.detection_evidence,
                },
            )

            # ── Phase 3: Forward to Manager ────────────────────────────
            response = await self._bridge.forward(
                session=session,
                manager=self._manager,
                migration_strategy=request.migration_strategy,
            )

            if response.success:
                logger.info(
                    "[InputGateway] Upload complete. project_id=%s session=%s",
                    response.project_id, session.session_id[:8],
                )
            else:
                logger.warning(
                    "[InputGateway] Manager forwarding failed. session=%s error=%s",
                    session.session_id[:8], response.error,
                )

            return response

        except Exception as exc:
            # Last-resort catch — the Gateway must never crash
            logger.error(
                "[InputGateway] Uncaught exception in process_upload: %s",
                exc, exc_info=True,
            )
            # We may not have a session at this point
            from akaal.gateway.models.gateway_session import GatewaySession
            emergency_session = GatewaySession(
                original_filename=request.file_path,
                requested_by=request.requested_by,
            )
            emergency_session.mark_failed(
                GatewayErrorCode.INTERNAL_ERROR, str(exc)
            )
            return self._build_rejection_response(emergency_session)

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _build_rejection_response(self, session: GatewaySession) -> GatewayResponse:
        """Convert a rejected/failed session into a GatewayResponse."""
        return GatewayResponse(
            success=False,
            session_id=session.session_id,
            migration_id=session.migration_id,
            detected_db_type=session.detected_db_type,
            detection_confidence=session.detection_confidence,
            status=session.status,
            message=session.error_message or "Upload was rejected.",
            original_filename=session.original_filename,
            file_size_bytes=session.file_size_bytes,
            table_count=session.table_count,
            estimated_row_count=session.estimated_row_count,
            warnings=session.warnings,
            error=GatewayError(
                code=session.error_code or GatewayErrorCode.INTERNAL_ERROR,
                message=session.error_message or "Unknown error.",
                requires_user_action=(
                    session.error_code == GatewayErrorCode.CONFIDENCE_TOO_LOW
                ),
            ),
        )
