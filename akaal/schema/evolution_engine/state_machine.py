"""
AKAAL Platform 5 — Evolution State Machine
"""

from akaal.schema.domain.enums import EvolutionState
from akaal.schema.domain.errors import ExecutionError


class EvolutionStateMachine:
    """Explicit Evolution State Machine."""

    ALLOWED_TRANSITIONS = {
        EvolutionState.CREATED: {EvolutionState.PLANNED, EvolutionState.FAILED},
        EvolutionState.PLANNED: {EvolutionState.VALIDATED, EvolutionState.FAILED},
        EvolutionState.VALIDATED: {EvolutionState.EXECUTING, EvolutionState.FAILED},
        EvolutionState.EXECUTING: {EvolutionState.VERIFYING, EvolutionState.FAILED, EvolutionState.ROLLED_BACK},
        EvolutionState.VERIFYING: {EvolutionState.COMPLETED, EvolutionState.FAILED, EvolutionState.ROLLED_BACK},
        EvolutionState.COMPLETED: set(),
        EvolutionState.FAILED: set(),
        EvolutionState.ROLLED_BACK: set(),
    }

    def __init__(self, initial_state: EvolutionState = EvolutionState.CREATED) -> None:
        self._state = initial_state

    @property
    def state(self) -> EvolutionState:
        return self._state

    def transition_to(self, new_state: EvolutionState) -> EvolutionState:
        allowed = self.ALLOWED_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            raise ExecutionError(
                message=f"Invalid evolution state transition from {self._state.value} to {new_state.value}.",
                recovery_recommendation="Halt schema evolution pipeline."
            )
        self._state = new_state
        return self._state
