"""
NexusForge — Manager Bridge
==============================
The ONLY component in the Input Gateway that communicates with the Manager Agent.

Architecture rule:
  The Input Gateway communicates with ONE and ONLY ONE agent: the Manager Agent.
  Direct communication with Scout, Validator, GB, or Live Intel is FORBIDDEN.

Responsibility:
  Translate a validated GatewaySession into the exact arguments that
  ManagerAgent.create_project() requires, then call it.

Target database handling:
  The Gateway only knows the source (the uploaded export file).
  The target database is set to SystemType.GENERIC with placeholder fields.
  The Manager or user will configure the actual target before migration runs.

Error handling:
  All Manager exceptions are caught and converted to structured GatewayResponse
  objects. The Manager Bridge never crashes the Gateway.

Timeout:
  asyncio.wait_for() enforces MANAGER_CALL_TIMEOUT_SECONDS.
  On timeout, returns a MANAGER_TIMEOUT GatewayError.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from akaal.audit.audit_logger import AuditEventType, AuditLogger
from akaal.core.models.enums import (
    GatewayStatus,
    MigrationStrategy,
    Priority,
    SystemType,
)
from akaal.core.models.project import ConnectionConfig, MigrationProject
from akaal.gateway.logging.gateway_logger import GatewayLogger
from akaal.gateway.models.gateway_request import GatewayRequest
from akaal.gateway.models.gateway_response import GatewayError, GatewayErrorCode, GatewayResponse
from akaal.gateway.models.gateway_session import GatewaySession


logger = logging.getLogger("nexusforge.gateway.manager_bridge")

# Seconds to wait for the Manager to accept the project creation request
MANAGER_CALL_TIMEOUT_SECONDS: float = 30.0

# Placeholder target config: used until the user configures an actual target
_GENERIC_TARGET_CONFIG = ConnectionConfig(
    system_type=SystemType.GENERIC,
    host="PENDING_CONFIGURATION",
    port=0,
    database_name="PENDING_CONFIGURATION",
    credentials_ref="PENDING_CONFIGURATION",
    read_only=False,   # Target is writable
    extra={"note": "Target database not yet configured. Set before running migration."},
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ManagerBridge:
    """
    Translates a validated GatewaySession into a Manager Agent project and
    calls ManagerAgent.create_project().

    This is the ONLY class in the Gateway allowed to communicate with the Manager.
    Any future Manager API changes are isolated here.

    Usage:
        bridge = ManagerBridge(audit_logger=audit_logger, gateway_logger=gw_logger)
        response = await bridge.forward(session, manager_agent, migration_strategy)
    """

    def __init__(
        self,
        audit_logger: AuditLogger,
        gateway_logger: Optional[GatewayLogger] = None,
        timeout_seconds: float = MANAGER_CALL_TIMEOUT_SECONDS,
    ) -> None:
        self._audit = audit_logger
        self._gw_log = gateway_logger or GatewayLogger()
        self._timeout = timeout_seconds

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    async def forward(
        self,
        session: GatewaySession,
        manager: object,  # ManagerAgent (typed as object to avoid circular import)
        migration_strategy: MigrationStrategy = MigrationStrategy.DRY_RUN,
    ) -> GatewayResponse:
        """
        Forward a validated GatewaySession to the Manager Agent.

        Builds a ConnectionConfig for the source, calls create_project(),
        and returns a structured GatewayResponse.

        Parameters
        ----------
        session : GatewaySession
            Must be in DETECTED status.
        manager : ManagerAgent
            The running Manager Agent instance.
        migration_strategy : MigrationStrategy
            Strategy to pass to the Manager.

        Returns
        -------
        GatewayResponse
            Always returned; never raises.
        """
        if session.status != GatewayStatus.DETECTED:
            return self._error_response(
                session,
                GatewayErrorCode.INTERNAL_ERROR,
                f"Cannot forward session in status {session.status.value}. Expected DETECTED.",
            )

        source_config = self._build_source_config(session)
        project_name = session.project_name or session.sanitized_filename or "Unnamed Migration"

        logger.info(
            "[ManagerBridge] Forwarding session=%s to Manager. db=%s strategy=%s",
            session.session_id[:8],
            session.detected_db_type,
            migration_strategy.value,
        )

        # Audit: Gateway about to forward
        self._audit.log(
            event_type=AuditEventType.GATEWAY_FORWARDED_TO_MANAGER,
            actor="INPUT_GATEWAY",
            description=f"Forwarding upload '{session.original_filename}' to Manager Agent.",
            details={
                "session_id": session.session_id,
                "migration_id": session.migration_id,
                "detected_db_type": session.detected_db_type.value if session.detected_db_type else None,
                "confidence": session.detection_confidence,
                "file_size_bytes": session.file_size_bytes,
            },
        )

        try:
            project: MigrationProject = await asyncio.wait_for(
                manager.create_project(  # type: ignore[attr-defined]
                    name=project_name,
                    source_config=source_config,
                    target_config=_GENERIC_TARGET_CONFIG,
                    strategy=migration_strategy,
                    created_by=session.requested_by,
                ),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            return self._error_response(
                session,
                GatewayErrorCode.MANAGER_TIMEOUT,
                f"Manager Agent did not respond within {self._timeout:.0f}s timeout.",
                requires_user_action=False,
            )
        except RuntimeError as exc:
            # Manager raises RuntimeError when system is frozen
            return self._error_response(
                session,
                GatewayErrorCode.MANAGER_UNAVAILABLE,
                f"Manager refused the request: {exc}",
            )
        except ValueError as exc:
            # Manager raises ValueError for invalid inputs
            return self._error_response(
                session,
                GatewayErrorCode.MANAGER_REJECTED,
                f"Manager rejected the project: {exc}",
            )
        except Exception as exc:
            logger.error(
                "[ManagerBridge] Unexpected Manager error for session %s: %s",
                session.session_id[:8], exc, exc_info=True,
            )
            return self._error_response(
                session,
                GatewayErrorCode.INTERNAL_ERROR,
                f"Unexpected error communicating with Manager: {exc}",
            )

        # Success
        session.project_id = project.project_id
        session.manager_request_sent_at = _utc_now()
        session.transition_to(GatewayStatus.FORWARDED, f"Project {project.project_id} created.")

        self._gw_log.log_manager_request_sent(session, project.project_id)

        # Audit: success
        self._audit.log(
            event_type=AuditEventType.GATEWAY_FORWARDED_TO_MANAGER,
            actor="INPUT_GATEWAY",
            description=f"Project '{project_name}' created. ID={project.project_id}",
            details={
                "session_id": session.session_id,
                "project_id": project.project_id,
                "migration_id": session.migration_id,
            },
        )

        logger.info(
            "[ManagerBridge] Project created: id=%s session=%s",
            project.project_id, session.session_id[:8],
        )

        return GatewayResponse(
            success=True,
            session_id=session.session_id,
            migration_id=session.migration_id,
            project_id=project.project_id,
            detected_db_type=session.detected_db_type,
            detection_confidence=session.detection_confidence,
            status=GatewayStatus.FORWARDED,
            message=(
                f"Upload accepted. Project '{project_name}' created "
                f"(ID: {project.project_id}). "
                f"Detected database: {session.detected_db_type.value if session.detected_db_type else 'Unknown'}."
            ),
            original_filename=session.original_filename,
            file_size_bytes=session.file_size_bytes,
            table_count=session.table_count,
            estimated_row_count=session.estimated_row_count,
            warnings=session.warnings,
            error=None,
        )

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _build_source_config(self, session: GatewaySession) -> ConnectionConfig:
        """
        Build a ConnectionConfig representing the uploaded file as the source.

        The source is the uploaded export file, so host/port are set to
        placeholder values. SystemType reflects the detected database vendor.
        """
        db_type = session.detected_db_type or SystemType.GENERIC
        return ConnectionConfig(
            system_type=db_type,
            host="FILE_UPLOAD",          # No live connection; source is a file
            port=0,
            database_name=session.sanitized_filename or session.original_filename,
            credentials_ref="FILE_UPLOAD_NO_CREDENTIALS",
            read_only=True,              # Source is always read-only in NexusForge
            extra={
                "gateway_session_id": session.session_id,
                "migration_id": session.migration_id,
                "original_filename": session.original_filename,
                "file_format": session.file_format.value if session.file_format else None,
                "detection_confidence": session.detection_confidence,
                "detection_evidence": session.detection_evidence,
                "table_count": session.table_count,
                "estimated_row_count": session.estimated_row_count,
                "schema_hints": session.schema_hints,
            },
        )

    def _error_response(
        self,
        session: GatewaySession,
        error_code: str,
        message: str,
        requires_user_action: bool = False,
    ) -> GatewayResponse:
        """Build a failure GatewayResponse and log the error."""
        self._gw_log.log_error(session, error_code, message)
        self._audit.log(
            event_type=AuditEventType.GATEWAY_REJECTED,
            actor="INPUT_GATEWAY",
            description=f"Gateway forwarding failed: {error_code}",
            details={
                "session_id": session.session_id,
                "error_code": error_code,
                "message": message,
            },
        )
        session.mark_rejected(error_code, message)
        return GatewayResponse(
            success=False,
            session_id=session.session_id,
            migration_id=session.migration_id,
            detected_db_type=session.detected_db_type,
            detection_confidence=session.detection_confidence,
            status=session.status,
            message=message,
            original_filename=session.original_filename,
            file_size_bytes=session.file_size_bytes,
            warnings=session.warnings,
            error=GatewayError(
                code=error_code,
                message=message,
                requires_user_action=requires_user_action,
            ),
        )
