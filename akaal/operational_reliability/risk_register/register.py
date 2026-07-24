"""
AKAAL Platform 7 — Operational Risk Register.
"""

from typing import Dict, List, Optional
import uuid
from akaal.operational_reliability.domain.models import OperationalRisk
from akaal.operational_reliability.domain.enums import RiskSeverity


class OperationalRiskRegister:
    """Tracks operational risks, severity classification, residual risks, and mitigation plans."""

    def __init__(self) -> None:
        self._risks: Dict[str, OperationalRisk] = {}

    def register_risk(self, service_id: str, title: str, severity: RiskSeverity, mitigation_plan: str, residual_risk_score: float) -> OperationalRisk:
        risk_id = f"rsk-{uuid.uuid4().hex[:8]}"
        risk = OperationalRisk(
            risk_id=risk_id,
            service_id=service_id,
            title=title,
            severity=severity,
            mitigation_plan=mitigation_plan,
            residual_risk_score=residual_risk_score,
        )
        self._risks[risk_id] = risk
        return risk

    def list_risks_for_service(self, service_id: str) -> List[OperationalRisk]:
        return [r for r in self._risks.values() if r.service_id == service_id]
