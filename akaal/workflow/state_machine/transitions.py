"""Explicit State Machine Transition Graph & Transition Validation Rules."""

from akaal.workflow.state_machine.states import WorkflowState

# Explicit Transition Matrix Mapping: Source State -> Set of Allowed Target States
_ALLOWED_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.CREATED: {
        WorkflowState.READY,
        WorkflowState.CANCELLED,
    },
    WorkflowState.READY: {
        WorkflowState.RUNNING,
        WorkflowState.CANCELLED,
    },
    WorkflowState.RUNNING: {
        WorkflowState.PAUSING,
        WorkflowState.WAITING_FOR_APPROVAL,
        WorkflowState.COMPLETED,
        WorkflowState.ROLLING_BACK,
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
    },
    WorkflowState.PAUSING: {
        WorkflowState.PAUSED,
        WorkflowState.FAILED,
    },
    WorkflowState.PAUSED: {
        WorkflowState.RUNNING,  # Transients back via engine.resume()
        WorkflowState.CANCELLED,
    },
    WorkflowState.WAITING_FOR_APPROVAL: {
        WorkflowState.RUNNING,  # Transients back via engine.resume()
        WorkflowState.ROLLING_BACK,
        WorkflowState.CANCELLED,
    },
    WorkflowState.RECOVERING: {
        WorkflowState.READY,
        WorkflowState.RUNNING,
        WorkflowState.FAILED,
    },
    WorkflowState.ROLLING_BACK: {
        WorkflowState.ROLLED_BACK,
        WorkflowState.FAILED,
    },
    WorkflowState.COMPLETED: set(),  # Terminal state
    WorkflowState.ROLLED_BACK: set(),  # Terminal state
    WorkflowState.FAILED: {
        WorkflowState.ROLLING_BACK,
        WorkflowState.RECOVERING,  # Transients back via restart/retry
    },
    WorkflowState.CANCELLED: set(),  # Terminal state
}

_TERMINAL_STATES: set[WorkflowState] = {
    WorkflowState.COMPLETED,
    WorkflowState.ROLLED_BACK,
    WorkflowState.CANCELLED,
}


class TransitionGraph:
    """Validator for Workflow State Machine transitions."""

    @staticmethod
    def is_valid_transition(from_state: WorkflowState, to_state: WorkflowState) -> bool:
        """Check if transition from `from_state` to `to_state` is valid."""
        allowed = _ALLOWED_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    @staticmethod
    def get_allowed_transitions(from_state: WorkflowState) -> set[WorkflowState]:
        """Return copy of allowed target states for given state."""
        return set(_ALLOWED_TRANSITIONS.get(from_state, set()))

    @staticmethod
    def is_terminal_state(state: WorkflowState) -> bool:
        """Check if given state is a terminal state."""
        return state in _TERMINAL_STATES
