"""
tests.unit.engine_extensions.test_lifecycle
==========================================
Tests for extension lifecycle state machine transitions and invalid transition rejection.
"""

import pytest
from akaalEngine.extensions.lifecycle.manager import LifecycleManager
from akaalEngine.extensions.lifecycle.transitions import LifecycleStateMachine
from akaalEngine.extensions.models.enums import ExtensionLifecycleState
from akaalEngine.extensions.models.identity import ExtensionId, RegistryGeneration
from akaalEngine.extensions.errors.taxonomy import LifecycleTransitionError


def test_legal_lifecycle_transitions():
    lm = LifecycleManager()
    ext_id = ExtensionId("test-ext")
    gen = RegistryGeneration(1)

    assert lm.get_state(ext_id) == ExtensionLifecycleState.DISCOVERED

    # DISCOVERED -> REGISTERED
    s1 = lm.transition_state(ext_id, ExtensionLifecycleState.REGISTERED, gen, "Registered")
    assert s1.current_state == ExtensionLifecycleState.REGISTERED

    # REGISTERED -> ACTIVE
    s2 = lm.transition_state(ext_id, ExtensionLifecycleState.ACTIVE, gen, "Activated")
    assert s2.current_state == ExtensionLifecycleState.ACTIVE

    # ACTIVE -> INACTIVE
    s3 = lm.transition_state(ext_id, ExtensionLifecycleState.INACTIVE, gen, "Deactivated")
    assert s3.current_state == ExtensionLifecycleState.INACTIVE

    # INACTIVE -> ACTIVE
    s4 = lm.transition_state(ext_id, ExtensionLifecycleState.ACTIVE, gen, "Reactivated")
    assert s4.current_state == ExtensionLifecycleState.ACTIVE

    # ACTIVE -> REMOVED
    s5 = lm.transition_state(ext_id, ExtensionLifecycleState.REMOVED, gen, "Unregistered")
    assert s5.current_state == ExtensionLifecycleState.REMOVED


def test_illegal_lifecycle_transitions_fail_closed():
    ext_id = ExtensionId("bad-transition-ext")
    gen = RegistryGeneration(1)

    # Cannot transition directly from DISCOVERED to ACTIVE
    with pytest.raises(LifecycleTransitionError) as exc_info:
        LifecycleStateMachine.validate_transition(
            target_id=ext_id.value,
            current_state=ExtensionLifecycleState.DISCOVERED,
            new_state=ExtensionLifecycleState.ACTIVE,
        )
    assert "cannot move from 'DISCOVERED' to 'ACTIVE'" in str(exc_info.value)

    # Cannot transition out of terminal state REMOVED
    with pytest.raises(LifecycleTransitionError) as exc_info2:
        LifecycleStateMachine.validate_transition(
            target_id=ext_id.value,
            current_state=ExtensionLifecycleState.REMOVED,
            new_state=ExtensionLifecycleState.ACTIVE,
        )
    assert "cannot move from 'REMOVED'" in str(exc_info2.value)
