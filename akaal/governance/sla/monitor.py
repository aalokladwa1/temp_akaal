"""
AKAAL Platform 6 — Approval SLA Monitoring Engine.
"""

from typing import List, Dict, Any
from akaal.governance.domain.models import ApprovalWorkflow
from akaal.governance.domain.enums import ApprovalStatus


class SLAMonitoringService:
    """Tracks approval latencies and SLA compliance metrics."""

    def compute_sla_metrics(self, workflows: List[ApprovalWorkflow]) -> Dict[str, Any]:
        total = len(workflows)
        if total == 0:
            return {"sla_compliance_rate": 100.0, "total_workflows": 0, "breached_workflows": 0}

        breached = sum(1 for wf in workflows if wf.status == ApprovalStatus.ESCALATED or wf.status == ApprovalStatus.EXPIRED)
        compliance_rate = ((total - breached) / total) * 100.0

        return {
            "sla_compliance_rate": round(compliance_rate, 2),
            "total_workflows": total,
            "breached_workflows": breached,
        }
