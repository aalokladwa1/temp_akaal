"""
AKAAL Platform 7 — Operational Readiness Assessment Engine.
"""

from typing import List
import datetime
import uuid
from akaal.operational_reliability.domain.models import OperationalReadinessReport


class ReadinessAssessmentEngine:
    """Evaluates pre-deployment operational readiness, infrastructure readiness, and risk posture."""

    def evaluate_readiness(self, target_system: str, health_ok: bool, runbook_exists: bool, slo_defined: bool) -> OperationalReadinessReport:
        report_id = f"ord-{uuid.uuid4().hex[:8]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        blockers = []
        if not health_ok:
            blockers.append("System health status is degraded.")
        if not runbook_exists:
            blockers.append("No operational runbook linked to service.")
        if not slo_defined:
            blockers.append("No active SLO target registered.")

        score = 100.0 - (len(blockers) * 30.0)
        score = max(0.0, score)
        is_ready = len(blockers) == 0

        posture = "OPTIMAL" if is_ready else ("NEEDS_ATTENTION" if score >= 40.0 else "HIGH_RISK")

        return OperationalReadinessReport(
            report_id=report_id,
            target_system=target_system,
            overall_readiness_score=score,
            is_deployment_ready=is_ready,
            risk_posture=posture,
            blockers=blockers,
            assessed_at=now,
        )
