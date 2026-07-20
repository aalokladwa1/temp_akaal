"""Unit tests for Workflow Immutable Models & Sub-Context Composition."""

import pytest
from dataclasses import FrozenInstanceError
from akaal.workflow.models import (
    ExecutionContext,
    RuntimeContext,
    UserContext,
    WorkflowContext,
    WorkflowMetadata,
    StepDefinition,
    WorkflowManifest,
    WorkflowCheckpoint,
    WorkflowStepResult,
    StepStatus,
)
from akaal.workflow.security import SecurityContext
from akaal.workflow.utils.serialization import verify_sha256


def test_immutable_sub_contexts():
    exec_ctx = ExecutionContext(workflow_id="wf-1", run_id="run-1")
    rt_ctx = RuntimeContext(environment_variables={"ENV": "test"})
    sec = SecurityContext(user_id="alice", tenant_id="tenant-a", permissions=("read", "execute"))
    user_ctx = UserContext(user_id="alice", tenant_id="tenant-a", security_context=sec)

    assert exec_ctx.workflow_id == "wf-1"
    assert rt_ctx.environment_variables["ENV"] == "test"
    assert user_ctx.security_context.user_id == "alice"
    assert user_ctx.security_context.has_permission("read")

    # Verify immutability
    with pytest.raises((FrozenInstanceError, AttributeError)):
        exec_ctx.workflow_id = "wf-2"  # type: ignore


def test_workflow_context_composition_root():
    exec_ctx = ExecutionContext(workflow_id="wf-1", run_id="run-1")
    context = WorkflowContext(execution_context=exec_ctx)

    assert context.workflow_id == "wf-1"
    assert context.run_id == "run-1"
    assert context.version == 1
    assert context.checksum != ""
    assert verify_sha256(context.to_dict(), context.checksum)

    # Test pure functional immutable update with_updates()
    updated = context.with_updates(
        execution_updates={"completed_steps": ("step-1",)},
        runtime_updates={"temporary_state": {"result": "success"}},
    )

    assert updated.version == 2
    assert updated.execution_context.completed_steps == ("step-1",)
    assert updated.runtime_context.temporary_state == {"result": "success"}
    # Original remains unchanged
    assert context.version == 1
    assert context.execution_context.completed_steps == ()


def test_workflow_manifest_checksum():
    metadata = WorkflowMetadata(workflow_id="wf-1", workflow_name="Test Workflow")
    step_1 = StepDefinition(step_id="step-1", step_type="ReferencePassStep", dependencies=())
    step_2 = StepDefinition(step_id="step-2", step_type="ReferencePassStep", dependencies=("step-1",))
    manifest = WorkflowManifest(
        metadata=metadata,
        step_definitions=(step_1, step_2),
        execution_graph={"step-2": ("step-1",)},
    )

    assert manifest.checksum != ""
    assert verify_sha256(manifest.to_dict(), manifest.checksum)
