"""Unit tests for WorkflowStepRegistry & Private _StepFactory Encapsulation."""

import pytest
from akaal.workflow.exceptions import StepNotFoundException
from akaal.workflow.registry import WorkflowStepRegistry
from akaal.workflow.steps import ReferencePassStep


def test_registry_register_and_resolve():
    registry = WorkflowStepRegistry()
    registry.register("ReferencePassStep", ReferencePassStep)

    assert "ReferencePassStep" in registry.list_registered_steps()

    # Resolve step
    step_instance = registry.resolve("ReferencePassStep", step_id="resolved-1", custom_output="out")
    assert step_instance.step_id == "resolved-1"
    assert isinstance(step_instance, ReferencePassStep)


def test_registry_unregistered_step_raises_exception():
    registry = WorkflowStepRegistry()
    with pytest.raises(StepNotFoundException):
        registry.resolve("NonExistentStep", step_id="s-1")


def test_registry_encapsulation_hides_factory():
    registry = WorkflowStepRegistry()
    # Confirm registry does NOT expose StepFactory as a public property or method
    assert not hasattr(registry, "factory")
    assert not hasattr(registry, "step_factory")
