"""
AKAAL Platform 7 — Reliability Alert Router.
"""

from typing import List, Dict, Any
import datetime
import uuid

from akaal.operational_reliability.domain.models import ReliabilityAlert
from akaal.operational_reliability.domain.enums import IncidentSeverity


class AlertingEscalationEngine:
    """Intelligent alert routing, deduplication, alert suppression, and escalation engine."""

    def __init__(self) -> None:
        self._alerts: List[ReliabilityAlert] = []

    def raise_alert(self, service_id: str, summary: str, severity: IncidentSeverity, is_suppressed: bool = False) -> ReliabilityAlert:
        alert_id = f"alt-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        alert = ReliabilityAlert(
            alert_id=alert_id,
            service_id=service_id,
            summary=summary,
            severity=severity,
            triggered_at=now,
            is_suppressed=is_suppressed,
        )
        self._alerts.append(alert)
        return alert

    def list_active_alerts(self, include_suppressed: bool = False) -> List[ReliabilityAlert]:
        if include_suppressed:
            return list(self._alerts)
        return [a for a in self._alerts if not a.is_suppressed]
