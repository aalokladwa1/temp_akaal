"""Exhaustive behavioral unit test suite for Eight Core Enterprise Workflow Features."""

import pytest
from akaal.workflow.approval.engine import ApprovalEngine
from akaal.workflow.approval.gate import ApprovalGateStep
from akaal.workflow.approval.models import ApprovalPrincipal, ApprovalStatus, PrincipalType
from akaal.workflow.concrete.cutover import CutoverWorkflow, CdcStopStep, FinalSyncStep, CutoverSwitchStep
from akaal.workflow.concrete.migration import MigrationWorkflow, MigrationStep
from akaal.workflow.concrete.pre_migration import (
    PreMigrationWorkflow,
    ScoutStep,
    RulebookStep,
    DecoderStep,
    RiskStep,
    PlannerStep,
    AdvisorStep,
    EnterpriseIntelligenceStep,
)
from akaal.workflow.concrete.rollback import RollbackWorkflow, RollbackStep
from akaal.workflow.concrete.validation import ValidationWorkflow, GBValidationStep
from akaal.workflow.engine.engine import WorkflowEngine
from akaal.workflow.events.dispatcher import InMemoryEventDispatcher
from akaal.workflow.events.events import (
    ApprovalGrantedEvent,
    ApprovalRequestedEvent,
    WorkflowCompletedEvent,
    WorkflowEvent,
    WorkflowStartedEvent,
)
from akaal.workflow.exceptions import WorkflowException
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.sub_contexts import ExecutionContext
from akaal.workflow.models.results import StepStatus
from akaal.workflow.registry.registry import WorkflowStepRegistry
from akaal.workflow.reporting.orchestrator import ReportOrchestrator
from akaal.workflow.reporting.reports import ReportFormat, WorkflowReportType
from akaal.workflow.utils.clock import FixedClock
from akaal.workflow.utils.id_generator import DeterministicIdGenerator


def _make_context(workflow_id: str, run_id: str) -> WorkflowContext:
    return WorkflowContext(execution_context=ExecutionContext(workflow_id=workflow_id, run_id=run_id))


def test_pre_migration_workflow_manifest_and_steps() -> None:
    manifest = PreMigrationWorkflow.build_manifest()
    assert manifest.metadata.workflow_id == "w_pre_migration"
    assert len(manifest.step_definitions) == 7

    context = _make_context("w_pre_migration", "run_101")
    scout = ScoutStep(step_id="step_scout")
    res = scout.execute(context)
    assert res.success is True
    assert res.status == StepStatus.COMPLETED
    assert "scout_output" in res.context_updates


def test_migration_workflow_manifest_and_steps() -> None:
    manifest = MigrationWorkflow.build_manifest()
    assert manifest.metadata.workflow_id == "w_migration"
    assert len(manifest.step_definitions) == 1

    context = _make_context("w_migration", "run_102")
    step = MigrationStep(step_id="step_migration_execute")
    res = step.execute(context)
    assert res.success is True
    assert res.status == StepStatus.COMPLETED
    assert res.context_updates["migration_output"]["rows_migrated"] == 150000


def test_validation_workflow_manifest_and_steps() -> None:
    manifest = ValidationWorkflow.build_manifest()
    assert manifest.metadata.workflow_id == "w_validation"
    assert len(manifest.step_definitions) == 1

    context = _make_context("w_validation", "run_103")
    step = GBValidationStep(step_id="step_gb_validation")
    res = step.execute(context)
    assert res.success is True
    assert res.status == StepStatus.COMPLETED
    assert res.context_updates["validation_output"]["gb_benchmark_passed"] is True


def test_cutover_workflow_manifest_and_steps() -> None:
    manifest = CutoverWorkflow.build_manifest()
    assert manifest.metadata.workflow_id == "w_cutover"
    assert len(manifest.step_definitions) == 3

    context = _make_context("w_cutover", "run_104")
    c1 = CdcStopStep("step_cdc_stop").execute(context)
    c2 = FinalSyncStep("step_final_sync").execute(context)
    c3 = CutoverSwitchStep("step_cutover_switch").execute(context)
    assert c1.status == StepStatus.COMPLETED
    assert c2.status == StepStatus.COMPLETED
    assert c3.status == StepStatus.COMPLETED


def test_rollback_workflow_manifest_and_steps() -> None:
    manifest = RollbackWorkflow.build_manifest()
    assert manifest.metadata.workflow_id == "w_rollback"
    assert len(manifest.step_definitions) == 1

    context = _make_context("w_rollback", "run_105")
    step = RollbackStep(step_id="step_rollback_execute")
    res = step.execute(context)
    assert res.success is True
    assert res.status == StepStatus.COMPLETED
    assert res.context_updates["rollback_output"]["rollback_status"] == "COMPLETED"


def test_three_gate_human_approval_engine_ordering_and_token() -> None:
    dispatcher = InMemoryEventDispatcher()
    clock = FixedClock("2026-01-01T12:00:00+00:00")
    id_gen = DeterministicIdGenerator()
    engine = ApprovalEngine(event_dispatcher=dispatcher, clock=clock, id_generator=id_gen)

    user = ApprovalPrincipal(principal_id="user_admin", principal_type=PrincipalType.USER, display_name="Admin User")

    # Request Gate 1
    req1 = engine.request_approval(workflow_id="w_e2e", gate_number=1, gate_name="Plan Readiness", assigned_principal=user)
    assert req1.gate_number == 1
    assert req1.status == ApprovalStatus.PENDING

    # Attempting Gate 2 before Gate 1 approved raises exception
    with pytest.raises(WorkflowException) as exc_info:
        engine.request_approval(workflow_id="w_e2e", gate_number=2, gate_name="Migration Progression", assigned_principal=user)
    assert "Cannot request Approval #2 before Approval #1 is approved" in str(exc_info.value)

    # Approve Gate 1
    token1 = engine.approve(req1.request_id, acting_principal=user)
    assert token1.status == ApprovalStatus.APPROVED
    assert token1.gate_number == 1

    # Now Request & Approve Gate 2
    req2 = engine.request_approval(workflow_id="w_e2e", gate_number=2, gate_name="Migration Progression", assigned_principal=user)
    token2 = engine.approve(req2.request_id, acting_principal=user)
    assert token2.gate_number == 2

    # Request & Approve Gate 3
    req3 = engine.request_approval(workflow_id="w_e2e", gate_number=3, gate_name="Final Cutover", assigned_principal=user)
    token3 = engine.approve(req3.request_id, acting_principal=user)
    assert token3.gate_number == 3

    assert len(dispatcher.dispatched_events) > 0


def test_approval_gate_step_execution_flow() -> None:
    engine = ApprovalEngine()
    user = ApprovalPrincipal(principal_id="role_lead", principal_type=PrincipalType.ROLE, display_name="Lead Role")
    gate_step = ApprovalGateStep(
        step_id="step_gate1",
        gate_number=1,
        gate_name="Plan Readiness",
        assigned_principal=user,
        approval_engine=engine,
    )
    context = _make_context("w_job_1", "run_1")

    # First execution: request created, returns SKIPPED (waiting for human sign-off)
    res1 = gate_step.execute(context)
    assert res1.status == StepStatus.SKIPPED

    # Find request and approve it
    req_id = list(engine._requests.keys())[0]
    engine.approve(req_id, acting_principal=user)

    # Second execution: token exists and approved, returns COMPLETED
    res2 = gate_step.execute(context)
    assert res2.status == StepStatus.COMPLETED
    assert res2.success is True


def test_report_orchestrator_json_and_markdown_rendering() -> None:
    dispatcher = InMemoryEventDispatcher()
    orchestrator = ReportOrchestrator(event_dispatcher=dispatcher)

    # Dispatch event
    dispatcher.dispatch(
        WorkflowEvent(
            event_id="e_101",
            event_type="PRE_MIGRATION_COMPLETE",
            workflow_id="w_demo",
            payload={"run_id": "run_demo", "tables_scouted": 12},
        )
    )

    report = orchestrator.get_report("w_demo", WorkflowReportType.PRE_MIGRATION)
    assert report is not None
    assert report.report_type == WorkflowReportType.PRE_MIGRATION
    assert "Pre-Migration" in report.render_markdown()
    assert '"PRE_MIGRATION"' in report.render_json()
