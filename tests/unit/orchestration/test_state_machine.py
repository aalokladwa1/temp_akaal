"""
Unit tests for Workflow State Machine and StateController.
"""

import pytest
from akaal.orchestration.domain.types import EngineState
from akaal.orchestration.domain.errors import InvalidStateTransitionError
from akaal.orchestration.engine.state_controller import StateController


def test_valid_state_transitions():
    controller = StateController()

    # CREATED -> READY -> RUNNING -> COMPLETED
    assert controller.transition(EngineState.CREATED, EngineState.READY) == EngineState.READY
    assert controller.transition(EngineState.READY, EngineState.RUNNING) == EngineState.RUNNING
    assert controller.transition(EngineState.RUNNING, EngineState.COMPLETED) == EngineState.COMPLETED

    # RUNNING -> WAITING_FOR_APPROVAL -> RUNNING
    assert controller.transition(EngineState.RUNNING, EngineState.WAITING_FOR_APPROVAL) == EngineState.WAITING_FOR_APPROVAL
    assert controller.transition(EngineState.WAITING_FOR_APPROVAL, EngineState.RUNNING) == EngineState.RUNNING

    # RUNNING -> PAUSED -> RUNNING
    assert controller.transition(EngineState.RUNNING, EngineState.PAUSED) == EngineState.PAUSED
    assert controller.transition(EngineState.PAUSED, EngineState.RUNNING) == EngineState.RUNNING

    # FAILED -> ROLLED_BACK -> READY
    assert controller.transition(EngineState.FAILED, EngineState.ROLLED_BACK) == EngineState.ROLLED_BACK
    assert controller.transition(EngineState.ROLLED_BACK, EngineState.READY) == EngineState.READY


def test_invalid_state_transitions():
    controller = StateController()

    # COMPLETED -> RUNNING is forbidden
    with pytest.raises(InvalidStateTransitionError):
        controller.validate_transition(EngineState.COMPLETED, EngineState.RUNNING)

    # FAILED -> READY is forbidden (must rollback or recover)
    with pytest.raises(InvalidStateTransitionError):
        controller.validate_transition(EngineState.FAILED, EngineState.READY)

    # CANCELLED -> RUNNING is forbidden
    with pytest.raises(InvalidStateTransitionError):
        controller.validate_transition(EngineState.CANCELLED, EngineState.RUNNING)

    # COMPLETED -> FAILED is forbidden
    with pytest.raises(InvalidStateTransitionError):
        controller.validate_transition(EngineState.COMPLETED, EngineState.FAILED)
