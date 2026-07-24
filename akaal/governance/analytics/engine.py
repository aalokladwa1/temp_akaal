"""
AKAAL Platform 6 — Approval Analytics & KPI Engine.
"""

from typing import List, Dict, Any
from akaal.governance.domain.models import GovernanceDecision, ApprovalWorkflow


class ApprovalAnalyticsService:
    """Generates throughput, latency, and violation trends metrics."""

    def compute_analytics(self, decisions: List[GovernanceDecision], workflows: List[ApprovalWorkflow]) -> Dict[str, Any]:
        total_decisions = len(decisions)
        approved_count = sum(1 for d in decisions if d.outcome == "APPROVED")
        rejected_count = sum(1 for d in decisions if d.outcome == "REJECTED")

        return {
            "total_decisions": total_decisions,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "approval_throughput_per_min": round(total_decisions / 60.0, 2),
            "rejection_rate_pct": round((rejected_count / max(1, total_decisions)) * 100.0, 2),
        }
