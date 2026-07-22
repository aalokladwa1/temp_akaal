"""
Unit tests for Human Approval Request Identifier Consistency Fix.
Verifies single canonical request identity, duplicate request prevention,
rejection propagation, and approval resumption.
"""

from akaal.workflow.approval.models import ApprovalPrincipal, ApprovalStatus, PrincipalType
from akaal.workflow.approval.engine import ApprovalEngine
from akaal.workflow.approval.gate import ApprovalGateStep
from akaal.workflow.models.sub_contexts import ExecutionContext
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.exceptions import WorkflowException


def test_canonical_approval_request_id_consistency():
    """Verify single canonical request ID across multiple step executions."""
    engine = ApprovalEngine()
    principal = ApprovalPrincipal("admin-user", PrincipalType.USER, "Admin User")

    step = ApprovalGateStep(
        step_id="start_gate_step",
        gate_number=1,
        gate_name="Start Authorization",
        assigned_principal=principal,
        approval_engine=engine,
    )

    ctx = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-canonical-1", run_id="run-1"))

    # Initial execution creates approval request
    res1 = step.execute(ctx)
    assert res1.success is False

    req1 = engine.get_request_for_gate("wf-canonical-1", 1)
    assert req1 is not None
    assert req1.status == ApprovalStatus.PENDING

    # Repeated execution must reuse same request ID
    res2 = step.execute(ctx)
    assert res2.success is False

    req2 = engine.get_request_for_gate("wf-canonical-1", 1)
    assert req2.request_id == req1.request_id

    # Grant approval
    token = engine.approve(req1.request_id, acting_principal=principal)
    assert token.status == ApprovalStatus.APPROVED

    # Execution resumes successfully
    res3 = step.execute(ctx)
    assert res3.success is True


def test_rejection_propagation_with_canonical_request_id():
    """Verify that rejection of a canonical request ID stops workflow progression."""
    engine = ApprovalEngine()
    principal = ApprovalPrincipal("admin-user", PrincipalType.USER, "Admin User")

    step = ApprovalGateStep(
        step_id="cutover_gate_step",
        gate_number=1,
        gate_name="Gate 1 Authorization",
        assigned_principal=principal,
        approval_engine=engine,
    )

    ctx = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-canonical-rej", run_id="run-2"))
    step.execute(ctx)

    req = engine.get_request_for_gate("wf-canonical-rej", 1)
    assert req is not None

    engine.reject(req.request_id, acting_principal=principal, reason="Security Threshold Violation")

    res_rej = step.execute(ctx)
    assert res_rej.success is False
    assert res_rej.status.value == "FAILED"
    assert "rejected" in res_rej.errors[0]
