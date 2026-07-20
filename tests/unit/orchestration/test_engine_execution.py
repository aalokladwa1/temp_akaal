"""
Unit and integration tests for Generic WorkflowEngine execution.
"""

import pytest
from typing import Dict, Any

from akaal.orchestration.domain.types import EngineState, WorkflowStepName
from akaal.orchestration.domain.errors import WorkflowExecutionError, InvalidStateTransitionError
from akaal.orchestration.models.job import MigrationJob
from akaal.orchestration.workflow.step import WorkflowStep
from akaal.orchestration.workflow.definition import WorkflowDefinition
from akaal.orchestration.workflow.context import WorkflowContext
from akaal.orchestration.config.config import UnifiedConfigurationManager
from akaal.orchestration.engine.engine import WorkflowEngine


class DummyAnalysisStep(WorkflowStep):
    def __init__(self) -> None:
        super().__init__(name=WorkflowStepName.ANALYSIS.value, description="Dummy analysis")
        self.initialized = False
        self.validated = False
        self.executed = False

    def initialize(self, context: WorkflowContext) -> None:
        self.initialized = True

    def validate(self, context: WorkflowContext) -> bool:
        self.validated = True
        return True

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        self.executed = True
        return {"tables_analyzed": 10}

    def checkpoint(self, context: WorkflowContext) -> Dict[str, Any]:
        return {"completed": True, "count": 10}

    def resume(self, context: WorkflowContext, checkpoint_data: Dict[str, Any]) -> None:
        pass

    def rollback(self, context: WorkflowContext) -> None:
        pass

    def cleanup(self, context: WorkflowContext) -> None:
        pass


class DummyMigrationStep(WorkflowStep):
    def __init__(self, fail: bool = False) -> None:
        super().__init__(name=WorkflowStepName.MIGRATION.value, description="Dummy migration")
        self.fail = fail
        self.rolled_back = False

    def initialize(self, context: WorkflowContext) -> None: pass
    def validate(self, context: WorkflowContext) -> bool: return True

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        if self.fail:
            raise RuntimeError("Simulated migration failure")
        return {"rows_migrated": 1000}

    def checkpoint(self, context: WorkflowContext) -> Dict[str, Any]:
        return {"rows_migrated": 1000}

    def resume(self, context: WorkflowContext, checkpoint_data: Dict[str, Any]) -> None: pass

    def rollback(self, context: WorkflowContext) -> None:
        self.rolled_back = True

    def cleanup(self, context: WorkflowContext) -> None: pass


def test_full_workflow_successful_execution():
    engine = WorkflowEngine()
    config = UnifiedConfigurationManager().build_config()

    step1 = DummyAnalysisStep()
    step2 = DummyMigrationStep()
    definition = WorkflowDefinition(
        name="test_pipeline",
        version="1.0.0",
        steps=[step1, step2],
    )

    job, session = engine.create_job(
        source_profile={"db": "sqlserver"},
        target_profile={"db": "oracle"},
        config=config,
    )

    completed_job = engine.execute_workflow(
        job=job,
        definition=definition,
        config=config,
        session=session,
    )

    assert completed_job.current_state == EngineState.COMPLETED
    assert step1.initialized and step1.validated and step1.executed
    assert completed_job.current_step == WorkflowStepName.MIGRATION.value

    # Verify audit records were generated
    records = engine.audit_repo.query_audit_records()
    assert len(records) > 0


def test_workflow_execution_failure_and_rollback():
    engine = WorkflowEngine()
    config = UnifiedConfigurationManager().build_config()

    step1 = DummyAnalysisStep()
    step2 = DummyMigrationStep(fail=True)
    definition = WorkflowDefinition(
        name="failing_pipeline",
        version="1.0.0",
        steps=[step1, step2],
    )

    job, session = engine.create_job(
        source_profile={"db": "sqlserver"},
        target_profile={"db": "oracle"},
        config=config,
    )

    with pytest.raises(WorkflowExecutionError):
        engine.execute_workflow(job, definition, config, session)

    failed_job = engine.workflow_repo.get_job(job.job_id)
    assert failed_job.current_state == EngineState.FAILED

    # Rollback
    rolled_back_job = engine.rollback_workflow(failed_job, definition, config, session)
    assert rolled_back_job.current_state == EngineState.ROLLED_BACK
    assert step2.rolled_back is True


def test_workflow_approval_pause():
    engine = WorkflowEngine()
    config = UnifiedConfigurationManager().build_config()

    step1 = DummyAnalysisStep()
    step2 = DummyMigrationStep()
    definition = WorkflowDefinition(
        name="approval_pipeline",
        version="1.0.0",
        steps=[step1, step2],
        approval_rules={
            WorkflowStepName.ANALYSIS.value: {"require_approval": True, "roles": ["ADMIN"]}
        },
    )

    job, session = engine.create_job(
        source_profile={"db": "source"},
        target_profile={"db": "target"},
        config=config,
    )

    paused_job = engine.execute_workflow(job, definition, config, session)
    assert paused_job.current_state == EngineState.WAITING_FOR_APPROVAL

    pending = engine.workflow_repo.get_pending_approvals(job.workflow_id)
    assert len(pending) == 1
    app_id = pending[0]["approval_id"]

    # Resolve approval
    engine.approval_coordinator.resolve_approval(job.workflow_id, app_id, approved=True)
    
    # Resume execution
    resumed_job = engine.resume_workflow(paused_job, definition, config, session)
    assert resumed_job.current_state == EngineState.COMPLETED
