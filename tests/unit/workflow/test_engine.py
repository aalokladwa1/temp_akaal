"""Unit tests for WorkflowEngine facade, pause/resume, cancel, and event dispatching."""

import pytest
from akaal.workflow.api import WorkflowClient
from akaal.workflow.events import InMemoryEventDispatcher
from akaal.workflow.models import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.state_machine import WorkflowState
from akaal.workflow.steps import ReferenceFailStep, ReferencePassStep


def test_workflow_engine_full_execution_flow():
    dispatcher = InMemoryEventDispatcher()
    client = WorkflowClient()
    client.engine._event_dispatcher = dispatcher

    client.register_step("ReferencePassStep", ReferencePassStep)
    meta = WorkflowMetadata(workflow_id="wf-engine-1", workflow_name="Full Workflow")
    s1 = StepDefinition(step_id="step-1", step_type="ReferencePassStep")
    s2 = StepDefinition(step_id="step-2", step_type="ReferencePassStep", dependencies=("step-1",))
    manifest = WorkflowManifest(metadata=meta, step_definitions=(s1, s2))

    client.submit_workflow(manifest)
    trace = client.execute_workflow("wf-engine-1")

    assert len(trace.step_results) == 2
    assert trace.step_results[0].success is True
    assert trace.step_results[1].success is True
    assert len(dispatcher.dispatched_events) > 0


def test_workflow_engine_step_failure():
    client = WorkflowClient()
    client.register_step("ReferenceFailStep", ReferenceFailStep)

    meta = WorkflowMetadata(workflow_id="wf-fail-1", workflow_name="Failing Workflow")
    s1 = StepDefinition(step_id="step-1", step_type="ReferenceFailStep")
    manifest = WorkflowManifest(metadata=meta, step_definitions=(s1,))

    client.submit_workflow(manifest)
    trace = client.execute_workflow("wf-fail-1")

    assert len(trace.step_results) == 1
    assert trace.step_results[0].success is False
    assert client.engine._state_controllers["wf-fail-1"].current_state == WorkflowState.FAILED


def test_workflow_engine_pause_and_resume():
    client = WorkflowClient()
    client.register_step("ReferencePassStep", ReferencePassStep)

    meta = WorkflowMetadata(workflow_id="wf-pause-1", workflow_name="Pausable Workflow")
    s1 = StepDefinition(step_id="step-1", step_type="ReferencePassStep")
    s2 = StepDefinition(step_id="step-2", step_type="ReferencePassStep", dependencies=("step-1",))
    manifest = WorkflowManifest(metadata=meta, step_definitions=(s1, s2))

    client.submit_workflow(manifest)
    client.pause_workflow("wf-pause-1")
    trace = client.execute_workflow("wf-pause-1")

    # Should pause after step-1
    assert client.engine._state_controllers["wf-pause-1"].current_state == WorkflowState.PAUSED

    # Resume workflow
    resume_trace = client.resume_workflow("wf-pause-1")
    assert client.engine._state_controllers["wf-pause-1"].current_state == WorkflowState.COMPLETED
