"""
AKAAL Platform 5 — Refresh State Machine

Enforces explicit lifecycle state transitions for metadata refresh routines.
"""

from akaal.schema.domain.enums import RefreshState
from akaal.schema.domain.errors import MetadataError


class RefreshStateMachine:
    """Explicit State Machine governing Metadata Refresh."""

    ALLOWED_TRANSITIONS = {
        RefreshState.IDLE: {RefreshState.QUEUED, RefreshState.REFRESHING},
        RefreshState.QUEUED: {RefreshState.REFRESHING, RefreshState.FAILED},
        RefreshState.REFRESHING: {RefreshState.COMPLETED, RefreshState.FAILED},
        RefreshState.COMPLETED: {RefreshState.IDLE, RefreshState.QUEUED, RefreshState.REFRESHING},
        RefreshState.FAILED: {RefreshState.IDLE, RefreshState.QUEUED, RefreshState.REFRESHING},
    }

    def __init__(self, initial_state: RefreshState = RefreshState.IDLE) -> None:
        self._current_state = initial_state

    @property
    def state(self) -> RefreshState:
        return self._current_state

    def transition_to(self, new_state: RefreshState) -> RefreshState:
        allowed = self.ALLOWED_TRANSITIONS.get(self._current_state, set())
        if new_state not in allowed:
            raise MetadataError(
                message=f"Invalid refresh state transition from {self._current_state} to {new_state}.",
                recovery_recommendation="Reset refresh state machine to IDLE."
            )
        self._current_state = new_state
        return self._current_state
