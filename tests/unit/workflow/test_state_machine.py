"""Unit tests for Workflow State Machine, Transition Graph, and StateController."""

import pytest
from akaal.workflow.exceptions import InvalidStateTransitionException
from akaal.workflow.state_machine import StateController, TransitionGraph, WorkflowState
from akaal.workflow.utils.clock import FixedClock


def test_valid_state_transitions():
    clock = FixedClock()
    controller = StateController(initial_state=WorkflowState.CREATED, clock=clock)

    assert controller.current_state == WorkflowState.CREATED

    # Valid path: CREATED -> READY -> RUNNING -> COMPLETED
    rec1 = controller.transition_to(WorkflowState.READY, "Manifest validated")
    assert controller.current_state == WorkflowState.READY
    assert rec1.from_state == WorkflowState.CREATED.value
    assert rec1.to_state == WorkflowState.READY.value

    controller.transition_to(WorkflowState.RUNNING, "Starting loop")
    assert controller.current_state == WorkflowState.RUNNING

    controller.transition_to(WorkflowState.COMPLETED, "Done")
    assert controller.current_state == WorkflowState.COMPLETED
    assert controller.is_terminal()
    assert len(controller.transition_records) == 3


def test_invalid_state_transitions():
    controller = StateController(initial_state=WorkflowState.CREATED)

    # CREATED -> COMPLETED is invalid
    with pytest.raises(InvalidStateTransitionException) as exc_info:
        controller.transition_to(WorkflowState.COMPLETED)

    assert exc_info.value.current_state == WorkflowState.CREATED.value
    assert exc_info.value.target_state == WorkflowState.COMPLETED.value


def test_pause_and_resume_transitions():
    controller = StateController(initial_state=WorkflowState.RUNNING)

    # RUNNING -> PAUSING -> PAUSED -> RUNNING
    controller.transition_to(WorkflowState.PAUSING, "Pause requested")
    assert controller.current_state == WorkflowState.PAUSING

    controller.transition_to(WorkflowState.PAUSED, "Paused at boundary")
    assert controller.current_state == WorkflowState.PAUSED

    # Resume Action transitions PAUSED back to RUNNING
    controller.transition_to(WorkflowState.RUNNING, "Resumed by user action")
    assert controller.current_state == WorkflowState.RUNNING
