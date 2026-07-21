"""
AKAAL Platform 5 — Transaction State Machine

Enforces legal state transitions across the SchemaTransaction lifecycle:
PENDING -> VALIDATING -> EXECUTING -> COMMITTED / ROLLING_BACK -> ROLLED_BACK / FAILED
"""

from akaal.schema.domain.enums import TransactionState
from akaal.schema.domain.errors import TransactionError


class TransactionStateMachine:
    """Explicit Transaction State Machine."""

    ALLOWED_TRANSITIONS = {
        TransactionState.PENDING: {TransactionState.VALIDATING, TransactionState.FAILED},
        TransactionState.VALIDATING: {TransactionState.EXECUTING, TransactionState.FAILED},
        TransactionState.EXECUTING: {TransactionState.COMMITTED, TransactionState.ROLLING_BACK, TransactionState.FAILED},
        TransactionState.ROLLING_BACK: {TransactionState.ROLLED_BACK, TransactionState.FAILED},
        TransactionState.COMMITTED: set(),
        TransactionState.ROLLED_BACK: set(),
        TransactionState.FAILED: set(),
    }

    def __init__(self, initial_state: TransactionState = TransactionState.PENDING) -> None:
        self._state = initial_state

    @property
    def state(self) -> TransactionState:
        return self._state

    def transition_to(self, new_state: TransactionState) -> TransactionState:
        allowed = self.ALLOWED_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            raise TransactionError(
                message=f"Invalid transaction transition from {self._state.value} to {new_state.value}.",
                recovery_recommendation="Rollback transaction and purge pending context."
            )
        self._state = new_state
        return self._state
