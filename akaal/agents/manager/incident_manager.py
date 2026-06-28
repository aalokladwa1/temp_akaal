"""
NexusForge — Incident Manager
================================
Automatically creates, tracks, and resolves incidents for all
system failures detected by any agent.

TRD Section 13 Incident Management: Manager shall automatically
create incidents for:
  Agent failure, Validation failure, GB mismatch,
  Adapter failure, Authentication failure,
  Infrastructure failure, Unexpected exceptions.

Every incident is:
  - Assigned a unique ID
  - Timestamped
  - Severity-classified
  - Logged to the audit trail
  - Stored in global state
  - Tracked until resolved
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.audit.audit_logger import AuditEventType, AuditLogger
from akaal.core.models.enums import AgentType, FailureReason, IncidentSeverity
from akaal.core.models.project import IncidentRecord
from akaal.core.state.global_state import GlobalState

logger = logging.getLogger("nexusforge.incident_manager")


# ---------------------------------------------------------------------------
# Severity Classification Rules
# ---------------------------------------------------------------------------

# Maps failure reasons to severity levels
FAILURE_SEVERITY_MAP: Dict[FailureReason, IncidentSeverity] = {
    FailureReason.CONNECTION_LOST:       IncidentSeverity.HIGH,
    FailureReason.PERMISSIONS_REVOKED:   IncidentSeverity.HIGH,
    FailureReason.METADATA_UNREADABLE:   IncidentSeverity.MEDIUM,
    FailureReason.SCHEMA_CORRUPTED:      IncidentSeverity.CRITICAL,
    FailureReason.CHECKSUM_MISMATCH:     IncidentSeverity.CRITICAL,
    FailureReason.VALIDATION_FAILED:     IncidentSeverity.HIGH,
    FailureReason.AGENT_TIMEOUT:         IncidentSeverity.MEDIUM,
    FailureReason.AUTHENTICATION_FAILED: IncidentSeverity.HIGH,
    FailureReason.INFRASTRUCTURE_ERROR:  IncidentSeverity.CRITICAL,
    FailureReason.ADAPTER_FAILURE:       IncidentSeverity.HIGH,
    FailureReason.DUPLICATE_REQUEST:     IncidentSeverity.LOW,
    FailureReason.UNAUTHORIZED_REQUEST:  IncidentSeverity.HIGH,
    FailureReason.LOOP_LIMIT_EXCEEDED:   IncidentSeverity.CRITICAL,
    FailureReason.UNKNOWN:               IncidentSeverity.MEDIUM,
}


class IncidentManager:
    """
    Creates, tracks, and resolves all system incidents.

    Integrated with GlobalState and AuditLogger.
    Used exclusively by the Manager Agent — no other agent
    creates incidents directly.
    """

    def __init__(
        self,
        global_state: GlobalState,
        audit_logger: AuditLogger,
    ) -> None:
        self._state = global_state
        self._audit = audit_logger
        # Local index: incident_id → IncidentRecord
        self._incidents: Dict[str, IncidentRecord] = {}
        logger.info("[IncidentManager] Initialized.")

    async def create_incident(
        self,
        project_id: str,
        migration_id: Optional[str],
        source_agent: AgentType,
        failure_reason: FailureReason,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        severity_override: Optional[IncidentSeverity] = None,
    ) -> IncidentRecord:
        """
        Create and register a new incident.

        TRD Section 13: Automatically create incidents for any system failure.

        Args:
            project_id: Associated project
            migration_id: Associated migration session
            source_agent: Agent that detected/caused the failure
            failure_reason: Classified reason
            description: Human-readable description
            details: Optional structured details dict
            severity_override: Override auto-classified severity if needed

        Returns the created IncidentRecord.
        """
        severity = severity_override or FAILURE_SEVERITY_MAP.get(
            failure_reason, IncidentSeverity.MEDIUM
        )

        incident = IncidentRecord(
            project_id=project_id,
            migration_id=migration_id,
            severity=severity.value,
            failure_reason=failure_reason.value,
            description=description,
            source_agent=source_agent.value,
        )

        # Store locally and in global state
        self._incidents[incident.incident_id] = incident
        await self._state.register_incident(incident)

        # Audit log
        self._audit.log(
            event_type=AuditEventType.INCIDENT_CREATED,
            actor=AgentType.MANAGER.value,
            description=f"Incident created: {description}",
            project_id=project_id,
            migration_id=migration_id,
            details={
                "incident_id": incident.incident_id,
                "severity": severity.value,
                "failure_reason": failure_reason.value,
                "source_agent": source_agent.value,
                **(details or {}),
            },
        )

        logger.warning(
            "[IncidentManager] Incident %s created. severity=%s reason=%s project=%s",
            incident.incident_id[:8], severity.value, failure_reason.value, project_id
        )
        return incident

    async def resolve_incident(
        self,
        incident_id: str,
        resolution_notes: str = "",
    ) -> bool:
        """
        Mark an incident as resolved.
        Returns True if found and resolved, False if not found.
        """
        incident = self._incidents.get(incident_id)
        if not incident:
            logger.warning("[IncidentManager] Incident %s not found.", incident_id[:8])
            return False

        incident.resolve(resolution_notes)
        await self._state.resolve_incident(incident_id, resolution_notes)

        self._audit.log(
            event_type=AuditEventType.INCIDENT_RESOLVED,
            actor=AgentType.MANAGER.value,
            description=f"Incident resolved: {incident_id}",
            project_id=incident.project_id,
            migration_id=incident.migration_id,
            details={"incident_id": incident_id, "notes": resolution_notes},
        )

        logger.info("[IncidentManager] Incident %s resolved.", incident_id[:8])
        return True

    def get_open_incidents(self, project_id: Optional[str] = None) -> List[IncidentRecord]:
        """Return all unresolved incidents, optionally filtered by project."""
        incidents = [i for i in self._incidents.values() if not i.is_resolved]
        if project_id:
            incidents = [i for i in incidents if i.project_id == project_id]
        return incidents

    def get_critical_incidents(self, project_id: Optional[str] = None) -> List[IncidentRecord]:
        """Return all unresolved CRITICAL incidents."""
        return [
            i for i in self.get_open_incidents(project_id)
            if i.severity == IncidentSeverity.CRITICAL.value
        ]

    def has_critical_incidents(self, project_id: str) -> bool:
        """Return True if this project has unresolved critical incidents."""
        return len(self.get_critical_incidents(project_id)) > 0

    def incident_count(self, project_id: Optional[str] = None) -> Dict[str, int]:
        """Return counts by severity for a project (or all projects)."""
        incidents = self.get_open_incidents(project_id)
        counts: Dict[str, int] = {s.value: 0 for s in IncidentSeverity}
        for i in incidents:
            counts[i.severity] = counts.get(i.severity, 0) + 1
        return counts

    def get_all_incidents(self) -> Dict[str, IncidentRecord]:
        return dict(self._incidents)

    def summary(self) -> Dict[str, Any]:
        total = len(self._incidents)
        open_count = len([i for i in self._incidents.values() if not i.is_resolved])
        return {
            "total_incidents": total,
            "open_incidents": open_count,
            "resolved_incidents": total - open_count,
            "open_by_severity": self.incident_count(),
        }
