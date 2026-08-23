"""
akaalEngine.extensions.lifecycle.transitions
============================================
Strict state machine governing ExtensionLifecycleState transitions.
Rejects illegal state transitions fail-closed.
"""

from __future__ import annotations

from typing import FrozenSet, Mapping

from akaalEngine.extensions.errors.taxonomy import LifecycleTransitionError
from akaalEngine.extensions.models.enums import ExtensionLifecycleState


# Legal state transition rules
_LEGAL_TRANSITIONS: Mapping[ExtensionLifecycleState, FrozenSet[ExtensionLifecycleState]] = {
    ExtensionLifecycleState.DISCOVERED: frozenset({
        ExtensionLifecycleState.REGISTERED,
        ExtensionLifecycleState.UNAVAILABLE,
        ExtensionLifecycleState.FAULTED,
        ExtensionLifecycleState.REMOVED,
    }),
    ExtensionLifecycleState.REGISTERED: frozenset({
        ExtensionLifecycleState.ACTIVE,
        ExtensionLifecycleState.INACTIVE,
        ExtensionLifecycleState.UNAVAILABLE,
        ExtensionLifecycleState.FAULTED,
        ExtensionLifecycleState.REMOVED,
    }),
    ExtensionLifecycleState.ACTIVE: frozenset({
        ExtensionLifecycleState.INACTIVE,
        ExtensionLifecycleState.UNAVAILABLE,
        ExtensionLifecycleState.FAULTED,
        ExtensionLifecycleState.REMOVED,
    }),
    ExtensionLifecycleState.INACTIVE: frozenset({
        ExtensionLifecycleState.ACTIVE,
        ExtensionLifecycleState.UNAVAILABLE,
        ExtensionLifecycleState.FAULTED,
        ExtensionLifecycleState.REMOVED,
    }),
    ExtensionLifecycleState.UNAVAILABLE: frozenset({
        ExtensionLifecycleState.ACTIVE,
        ExtensionLifecycleState.INACTIVE,
        ExtensionLifecycleState.REGISTERED,
        ExtensionLifecycleState.FAULTED,
        ExtensionLifecycleState.REMOVED,
    }),
    ExtensionLifecycleState.FAULTED: frozenset({
        ExtensionLifecycleState.REGISTERED,
        ExtensionLifecycleState.INACTIVE,
        ExtensionLifecycleState.REMOVED,
    }),
    ExtensionLifecycleState.REMOVED: frozenset({
        # Terminal state: Cannot transition out of REMOVED without a full re-registration transaction
    }),
}


class LifecycleStateMachine:
    """
    Validates lifecycle state transitions.
    """

    @classmethod
    def validate_transition(
        cls,
        target_id: str,
        current_state: ExtensionLifecycleState,
        new_state: ExtensionLifecycleState,
    ) -> None:
        if current_state == new_state:
            return  # No-op

        legal_targets = _LEGAL_TRANSITIONS.get(current_state, frozenset())
        if new_state not in legal_targets:
            raise LifecycleTransitionError(
                f"Illegal lifecycle transition for extension '{target_id}': cannot move from '{current_state.value}' to '{new_state.value}'."
            )
