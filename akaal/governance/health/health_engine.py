"""
AKAAL Platform 6 — Governance Health & Compliance Scoring Engine.
"""

import datetime
from akaal.governance.domain.models import GovernanceHealthScore


class GovernanceHealthEngine:
    """Continuously computes enterprise governance health score (0.0 to 100.0) and posture."""

    def compute_health(
        self,
        active_violations: int,
        sla_compliance_rate: float,
        unresolved_exceptions: int,
    ) -> GovernanceHealthScore:
        deductions = (active_violations * 10.0) + (unresolved_exceptions * 5.0) + max(0.0, (100.0 - sla_compliance_rate) * 0.5)
        raw_score = max(0.0, 100.0 - deductions)
        health_score = round(raw_score, 2)

        if health_score >= 90.0:
            posture = "OPTIMAL"
        elif health_score >= 75.0:
            posture = "STABLE"
        elif health_score >= 60.0:
            posture = "NEEDS_ATTENTION"
        else:
            posture = "CRITICAL_RISK"

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return GovernanceHealthScore(
            health_score=health_score,
            active_violations=active_violations,
            sla_compliance_rate=sla_compliance_rate,
            unresolved_exceptions=unresolved_exceptions,
            posture_status=posture,
            calculated_at=now,
        )
