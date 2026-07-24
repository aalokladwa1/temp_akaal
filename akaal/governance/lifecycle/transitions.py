"""
AKAAL Platform 6 — Governance Lifecycle Transitions.
"""

from typing import Tuple
from akaal.governance.domain.enums import LifecycleState
from akaal.governance.lifecycle.states import ALLOWED_STATE_TRANSITIONS


class LifecycleTransitionValidator:
    """Validates state transitions according to enterprise governance lifecycle rules."""

    def validate_transition(self, current_state: LifecycleState, target_state: LifecycleState) -> Tuple[bool, str]:
        allowed = ALLOWED_STATE_TRANSITIONS.get(current_state, [])
        if target_state not in allowed:
            return False, f"Invalid lifecycle transition: {current_state.value} -> {target_state.value}. Allowed: {[s.value for s in allowed]}"
        return True, "Transition allowed."
