"""
Enterprise Workflow State Machine Controller.
Validates state transitions explicitly and rejects illegal state transitions.
Engine states represent execution state only.
"""

from typing import Dict, FrozenSet, Set
import logging

from akaal.orchestration.domain.types import EngineState
from akaal.orchestration.domain.errors import InvalidStateTransitionError

logger = logging.getLogger("nexusforge.orchestration.state")


class StateController:
    """
    Explicit transition controller for EngineState transitions.
    Forbidden transitions (e.g. COMPLETED -> RUNNING, FAILED -> READY, CANCELLED -> RUNNING)
    raise InvalidStateTransitionError.
    """

    ALLOWED_TRANSITIONS: Dict[EngineState, FrozenSet[EngineState]] = {
        EngineState.CREATED: frozenset({
            EngineState.READY,
            EngineState.CANCELLED,
        }),
        EngineState.READY: frozenset({
            EngineState.RUNNING,
            EngineState.CANCELLED,
        }),
        EngineState.RUNNING: frozenset({
            EngineState.WAITING_FOR_APPROVAL,
            EngineState.PAUSED,
            EngineState.FAILED,
            EngineState.COMPLETED,
        }),
        EngineState.WAITING_FOR_APPROVAL: frozenset({
            EngineState.RUNNING,
            EngineState.PAUSED,
            EngineState.CANCELLED,
        }),
        EngineState.PAUSED: frozenset({
            EngineState.READY,
            EngineState.RUNNING,
            EngineState.CANCELLED,
        }),
        EngineState.FAILED: frozenset({
            EngineState.ROLLED_BACK,
        }),
        EngineState.ROLLED_BACK: frozenset({
            EngineState.READY,
            EngineState.CANCELLED,
        }),
        EngineState.COMPLETED: frozenset(),  # Terminal state
        EngineState.CANCELLED: frozenset(),  # Terminal state
    }

    def validate_transition(self, current_state: EngineState, target_state: EngineState) -> None:
        """
        Validates if transition from current_state to target_state is legal.
        Raises InvalidStateTransitionError if illegal.
        """
        if current_state == target_state:
            return  # Idempotent state re-affirmation is allowed

        allowed = self.ALLOWED_TRANSITIONS.get(current_state, frozenset())
        if target_state not in allowed:
            logger.error(
                f"Illegal state transition attempted: {current_state.value} -> {target_state.value}"
            )
            raise InvalidStateTransitionError(
                from_state=current_state.value,
                to_state=target_state.value,
                reason=f"Transition from {current_state.value} to {target_state.value} is strictly forbidden."
            )

    def transition(self, current_state: EngineState, target_state: EngineState) -> EngineState:
        """Validates and returns the target state if valid."""
        self.validate_transition(current_state, target_state)
        return target_state
