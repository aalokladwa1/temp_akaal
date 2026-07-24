"""
AKAAL Platform 7 — End-to-End Incident Lifecycle Manager.
"""

from typing import Dict, List, Optional
import datetime
import uuid

from akaal.operational_reliability.domain.models import Incident
from akaal.operational_reliability.domain.enums import IncidentSeverity, IncidentStatus
from akaal.operational_reliability.domain.exceptions import IncidentError


class IncidentManager:
    """Manages creation, severity classification, status updates, and resolution tracking for operational incidents."""

    def __init__(self) -> None:
        self._incidents: Dict[str, Incident] = {}

    def open_incident(
        self,
        title: str,
        severity: IncidentSeverity,
        impacted_services: List[str],
        lead_sre_id: str = "oncall_sre",
    ) -> Incident:
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        incident = Incident(
            incident_id=incident_id,
            title=title,
            severity=severity,
            status=IncidentStatus.OPEN,
            impacted_services=impacted_services,
            opened_at=now,
            resolved_at=None,
            root_cause_summary=None,
            lead_sre_id=lead_sre_id,
        )
        self._incidents[incident_id] = incident
        return incident

    def resolve_incident(self, incident_id: str, root_cause_summary: str) -> Incident:
        inc = self._incidents.get(incident_id)
        if not inc:
            raise IncidentError(f"Incident '{incident_id}' not found.")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        resolved = Incident(
            incident_id=inc.incident_id,
            title=inc.title,
            severity=inc.severity,
            status=IncidentStatus.RESOLVED,
            impacted_services=inc.impacted_services,
            opened_at=inc.opened_at,
            resolved_at=now,
            root_cause_summary=root_cause_summary,
            lead_sre_id=inc.lead_sre_id,
        )
        self._incidents[incident_id] = resolved
        return resolved

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self._incidents.get(incident_id)

    def list_open_incidents(self) -> List[Incident]:
        return [i for i in self._incidents.values() if i.status not in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]]
