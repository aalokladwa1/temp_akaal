"""Unit tests for ExecutionPipeline lifecycle hooks and success/failure branching."""

import pytest
from akaal.workflow.execution import ExecutionPipeline
from akaal.workflow.models import ExecutionContext, WorkflowContext
from akaal.workflow.models.results import StepStatus
from akaal.workflow.steps import ReferenceFailStep, ReferencePassStep, ReferencePreconditionFailStep
from akaal.workflow.utils import FixedClock


def test_execution_pipeline_success_branch():
    clock = FixedClock()
    pipeline = ExecutionPipeline(clock=clock)
    step = ReferencePassStep(step_id="pass-1", custom_output="value-1")
    context = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-1", run_id="run-1"))

    result, updated_context = pipeline.run_pipeline(step, context)

    assert result.success is True
    assert result.status == StepStatus.COMPLETED
    assert step.initialized is True
    assert step.success_hook_called is True
    assert step.failure_hook_called is False
    assert step.cleaned_up is True
    assert updated_context.runtime_context.temporary_state["pass-1"] == "value-1"


def test_execution_pipeline_failure_branch():
    clock = FixedClock()
    pipeline = ExecutionPipeline(clock=clock)
    step = ReferenceFailStep(step_id="fail-1", failure_message="Error in step")
    context = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-1", run_id="run-1"))

    result, updated_context = pipeline.run_pipeline(step, context)

    assert result.success is False
    assert step.initialized is True
    assert step.success_hook_called is False
    assert step.failure_hook_called is True
    assert step.rolled_back is True
    assert step.cleaned_up is True


def test_execution_pipeline_precondition_failure_branch():
    clock = FixedClock()
    pipeline = ExecutionPipeline(clock=clock)
    step = ReferencePreconditionFailStep(step_id="pre-fail-1")
    context = WorkflowContext(execution_context=ExecutionContext(workflow_id="wf-1", run_id="run-1"))

    result, updated_context = pipeline.run_pipeline(step, context)

    assert result.success is False
    assert step.failure_hook_called is True
    assert step.rolled_back is True
    assert step.cleaned_up is True
