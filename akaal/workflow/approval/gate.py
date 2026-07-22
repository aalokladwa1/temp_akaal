"""Approval Gate Step enforcing human sign-off before workflow progression."""

from typing import Optional
from akaal.workflow.approval.engine import ApprovalEngine
from akaal.workflow.approval.models import ApprovalPrincipal, ApprovalStatus, PrincipalType
from akaal.workflow.exceptions import PreconditionFailedException, WorkflowException
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.results import StepStatus, ValidationResult, WorkflowStepResult
from akaal.workflow.steps.reference_steps import AbstractStep


class ApprovalGateStep(AbstractStep):
    """Step that enforces human authorization at specific approval gates (Gate 1, 2, or 3)."""

    def __init__(
        self,
        step_id: str,
        gate_number: int,
        gate_name: str,
        assigned_principal: ApprovalPrincipal,
        approval_engine: ApprovalEngine,
    ) -> None:
        super().__init__(step_id)
        self.gate_number = gate_number
        self.gate_name = gate_name
        self.assigned_principal = assigned_principal
        self.approval_engine = approval_engine

    def validate_preconditions(self, context: WorkflowContext) -> ValidationResult:
        if self.gate_number < 1 or self.gate_number > 3:
            return ValidationResult(valid=False, errors=(f"Invalid gate number {self.gate_number}. Must be 1, 2, or 3.",))
        return ValidationResult(valid=True)

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        token = self.approval_engine.get_token(context.workflow_id, self.gate_number)
        if token and token.status == ApprovalStatus.APPROVED:
            return WorkflowStepResult(
                step_id=self.step_id,
                success=True,
                status=StepStatus.COMPLETED,
                context_updates={"approval_token": token.to_dict()},
            )

        # Token not approved yet. Ensure request exists.
        req = self.approval_engine.get_request_for_gate(context.workflow_id, self.gate_number)
        if not req:
            req = self.approval_engine.request_approval(
                workflow_id=context.workflow_id,
                gate_number=self.gate_number,
                gate_name=self.gate_name,
                assigned_principal=self.assigned_principal,
            )

        if req.status == ApprovalStatus.REJECTED:
            return WorkflowStepResult(
                step_id=self.step_id,
                success=False,
                status=StepStatus.FAILED,
                errors=(f"Approval #{self.gate_number} ({self.gate_name}) was rejected.",),
            )

        # Return status indicating waiting for approval
        return WorkflowStepResult(
            step_id=self.step_id,
            success=False,
            status=StepStatus.SKIPPED,
            warnings=(f"Workflow paused at Gate #{self.gate_number} waiting for human approval.",),
        )
