"""Thread-safe State Controller for Workflow State Machine."""

import threading
from typing import Tuple
from akaal.workflow.exceptions import InvalidStateTransitionException
from akaal.workflow.execution_records.records import StateTransitionRecord
from akaal.workflow.state_machine.states import WorkflowState
from akaal.workflow.state_machine.transitions import TransitionGraph
from akaal.workflow.utils.clock import IClock, SystemClock


class StateController:
    """Thread-safe state machine manager enforcing explicit transitions and producing audit records."""

    def __init__(
        self,
        initial_state: WorkflowState = WorkflowState.CREATED,
        clock: IClock | None = None,
    ) -> None:
        self._state = initial_state
        self._clock = clock or SystemClock()
        self._lock = threading.Lock()
        self._records: list[StateTransitionRecord] = []

    @property
    def current_state(self) -> WorkflowState:
        with self._lock:
            return self._state

    @property
    def transition_records(self) -> Tuple[StateTransitionRecord, ...]:
        with self._lock:
            return tuple(self._records)

    def transition_to(self, target_state: WorkflowState, reason: str = "") -> StateTransitionRecord:
        """Atomically transition state if allowed, otherwise raise InvalidStateTransitionException."""
        with self._lock:
            if not TransitionGraph.is_valid_transition(self._state, target_state):
                raise InvalidStateTransitionException(
                    current_state=self._state.value,
                    target_state=target_state.value,
                    reason=reason or f"Transition from {self._state.value} to {target_state.value} is not allowed.",
                )
            
            record = StateTransitionRecord(
                from_state=self._state.value,
                to_state=target_state.value,
                timestamp=self._clock.now_utc(),
                reason=reason,
            )
            self._state = target_state
            self._records.append(record)
            return record

    def is_terminal(self) -> bool:
        """Return true if current state is a terminal state."""
        with self._lock:
            return TransitionGraph.is_terminal_state(self._state)
