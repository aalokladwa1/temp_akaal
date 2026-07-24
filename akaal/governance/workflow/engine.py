"""
AKAAL Platform 6 — Approval Workflow Engine & Router.
"""

from typing import Dict, List, Optional
import datetime
import uuid

from akaal.governance.domain.models import ApprovalWorkflow, ApprovalStep
from akaal.governance.domain.enums import ApprovalStatus


class ApprovalWorkflowEngine:
    """Manages creation, execution, state transitions, and step resolution for governance workflows."""

    def __init__(self) -> None:
        self._workflows: Dict[str, ApprovalWorkflow] = {}

    def create_workflow(
        self,
        operation_type: str,
        target_platform: str,
        requester_id: str,
        required_roles: List[str],
        risk_score: float,
        is_four_eyes_required: bool,
    ) -> ApprovalWorkflow:
        workflow_id = f"wf-gov-{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        due_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)).isoformat()

        steps = [
            ApprovalStep(
                step_id=f"step-{i+1}",
                level=i+1,
                required_role=role,
                status=ApprovalStatus.PENDING,
            )
            for i, role in enumerate(required_roles)
        ]

        wf = ApprovalWorkflow(
            workflow_id=workflow_id,
            operation_type=operation_type,
            target_platform=target_platform,
            requester_id=requester_id,
            steps=steps,
            risk_score=risk_score,
            is_four_eyes_required=is_four_eyes_required,
            status=ApprovalStatus.PENDING,
            created_at=now,
            sla_due_at=due_at,
        )
        self._workflows[workflow_id] = wf
        return wf

    def get_workflow(self, workflow_id: str) -> Optional[ApprovalWorkflow]:
        return self._workflows.get(workflow_id)

    def record_step_decision(self, workflow_id: str, step_id: str, approver_id: str, approved: bool, comments: str = "") -> ApprovalWorkflow:
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        updated_steps = []
        all_approved = True
        any_rejected = False

        for step in wf.steps:
            if step.step_id == step_id:
                new_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                step = ApprovalStep(
                    step_id=step.step_id,
                    level=step.level,
                    required_role=step.required_role,
                    approver_id=approver_id,
                    status=new_status,
                    decided_at=now,
                    comments=comments,
                )
            if step.status != ApprovalStatus.APPROVED:
                all_approved = False
            if step.status == ApprovalStatus.REJECTED:
                any_rejected = True
            updated_steps.append(step)

        new_status = wf.status
        if any_rejected:
            new_status = ApprovalStatus.REJECTED
        elif all_approved:
            new_status = ApprovalStatus.APPROVED

        updated_wf = ApprovalWorkflow(
            workflow_id=wf.workflow_id,
            operation_type=wf.operation_type,
            target_platform=wf.target_platform,
            requester_id=wf.requester_id,
            steps=updated_steps,
            risk_score=wf.risk_score,
            is_four_eyes_required=wf.is_four_eyes_required,
            status=new_status,
            created_at=wf.created_at,
            sla_due_at=wf.sla_due_at,
        )
        self._workflows[workflow_id] = updated_wf
        return updated_wf
