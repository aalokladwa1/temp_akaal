"""
AKAAL Platform 6 — Approval Escalation Engine.
"""

from typing import List, Dict, Any
import datetime
from akaal.governance.domain.models import ApprovalWorkflow
from akaal.governance.domain.enums import ApprovalStatus


class EscalationEngine:
    """Monitors SLA deadlines and escalates overdue approvals to higher management hierarchy."""

    def __init__(self) -> None:
        self._escalation_log: List[Dict[str, Any]] = []

    def check_and_escalate(self, workflows: List[ApprovalWorkflow]) -> List[ApprovalWorkflow]:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        escalated_workflows = []

        for wf in workflows:
            if wf.status == ApprovalStatus.PENDING and wf.sla_due_at and wf.sla_due_at < now:
                # Log escalation event
                self._escalation_log.append({
                    "workflow_id": wf.workflow_id,
                    "escalated_at": now,
                    "previous_status": wf.status,
                    "target_role": "ExecutiveApprover",
                })
                # Create escalated copy
                escalated_wf = ApprovalWorkflow(
                    workflow_id=wf.workflow_id,
                    operation_type=wf.operation_type,
                    target_platform=wf.target_platform,
                    requester_id=wf.requester_id,
                    steps=wf.steps,
                    risk_score=wf.risk_score,
                    is_four_eyes_required=wf.is_four_eyes_required,
                    status=ApprovalStatus.ESCALATED,
                    created_at=wf.created_at,
                    sla_due_at=wf.sla_due_at,
                )
                escalated_workflows.append(escalated_wf)

        return escalated_workflows

    def get_escalation_log(self) -> List[Dict[str, Any]]:
        return list(self._escalation_log)
