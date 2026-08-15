"""
AKAAL CDC Engine Lifecycle State Machine & Acknowledgement Contracts.
=====================================================================
Defines strict acknowledgement states (CAPTURED -> DURABLY_BUFFERED -> APPLYING -> APPLIED -> CHECKPOINTED -> ACKNOWLEDGED)
and CDC Session State Machine (CREATED -> INITIALIZING -> CAPTURING -> ... -> CUTOVER_COMPLETE).
"""

from enum import Enum
from typing import Dict, Any, Set


class CDCAckState(str, Enum):
    """Event-level acknowledgement state machine."""
    CAPTURED = "CAPTURED"
    DURABLY_BUFFERED = "DURABLY_BUFFERED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    CHECKPOINTED = "CHECKPOINTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"

    @classmethod
    def can_transition(cls, current: "CDCAckState", target: "CDCAckState") -> bool:
        """Enforces strict, unskippable event lifecycle progression."""
        LEGAL_ACK_TRANSITIONS = {
            cls.CAPTURED: {cls.DURABLY_BUFFERED, cls.FAILED},
            cls.DURABLY_BUFFERED: {cls.APPLYING, cls.FAILED},
            cls.APPLYING: {cls.APPLIED, cls.FAILED},
            cls.APPLIED: {cls.CHECKPOINTED, cls.FAILED},
            cls.CHECKPOINTED: {cls.ACKNOWLEDGED, cls.FAILED},
            cls.ACKNOWLEDGED: set(),  # Terminal
            cls.FAILED: set(),  # Terminal for this event attempt
        }
        allowed = LEGAL_ACK_TRANSITIONS.get(current, set())
        return target in allowed


class CDCSessionState(str, Enum):
    """CDC Session lifecycle states."""
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    CAPTURING = "CAPTURING"
    BUFFERING = "BUFFERING"
    APPLYING = "APPLYING"
    CATCHING_UP = "CATCHING_UP"
    SYNCHRONIZED = "SYNCHRONIZED"
    PAUSED = "PAUSED"
    CUTOVER_PREPARING = "CUTOVER_PREPARING"
    FINAL_DRAIN = "FINAL_DRAIN"
    VALIDATING = "VALIDATING"
    CUTOVER_READY = "CUTOVER_READY"
    CUTOVER_COMPLETE = "CUTOVER_COMPLETE"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal CDC session state transition is attempted."""
    pass


class CDCSessionStateMachine:
    """Enforces legal CDC Session lifecycle state transitions."""

    LEGAL_TRANSITIONS: Dict[CDCSessionState, Set[CDCSessionState]] = {
        CDCSessionState.CREATED: {CDCSessionState.INITIALIZING, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.INITIALIZING: {CDCSessionState.CAPTURING, CDCSessionState.BUFFERING, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.CAPTURING: {CDCSessionState.BUFFERING, CDCSessionState.APPLYING, CDCSessionState.CATCHING_UP, CDCSessionState.PAUSED, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.BUFFERING: {CDCSessionState.APPLYING, CDCSessionState.CATCHING_UP, CDCSessionState.PAUSED, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.APPLYING: {CDCSessionState.CATCHING_UP, CDCSessionState.SYNCHRONIZED, CDCSessionState.PAUSED, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.CATCHING_UP: {CDCSessionState.SYNCHRONIZED, CDCSessionState.PAUSED, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.SYNCHRONIZED: {CDCSessionState.CUTOVER_PREPARING, CDCSessionState.PAUSED, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.PAUSED: {CDCSessionState.CAPTURING, CDCSessionState.APPLYING, CDCSessionState.CATCHING_UP, CDCSessionState.TERMINATED},
        CDCSessionState.CUTOVER_PREPARING: {CDCSessionState.FINAL_DRAIN, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.FINAL_DRAIN: {CDCSessionState.VALIDATING, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.VALIDATING: {CDCSessionState.CUTOVER_READY, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.CUTOVER_READY: {CDCSessionState.CUTOVER_COMPLETE, CDCSessionState.FAILED, CDCSessionState.TERMINATED},
        CDCSessionState.CUTOVER_COMPLETE: set(),  # Terminal state - no resurrection permitted!
        CDCSessionState.FAILED: {CDCSessionState.INITIALIZING, CDCSessionState.TERMINATED},  # Can only re-initialize cleanly
        CDCSessionState.TERMINATED: set(),  # Terminal state - no resurrection permitted!
    }

    def __init__(self, migration_id: str, job_id: str, run_id: str, cdc_session_id: str) -> None:
        self.migration_id = migration_id
        self.job_id = job_id
        self.run_id = run_id
        self.cdc_session_id = cdc_session_id
        self.current_state = CDCSessionState.CREATED

    def transition_to(self, target_state: CDCSessionState) -> CDCSessionState:
        """Transitions to target_state if legal; raises InvalidStateTransitionError if illegal."""
        allowed = self.LEGAL_TRANSITIONS.get(self.current_state, set())
        if target_state not in allowed:
            raise InvalidStateTransitionError(
                f"[CDC STATE ERROR] Illegal transition from '{self.current_state.value}' to '{target_state.value}' "
                f"for session '{self.cdc_session_id}' (run '{self.run_id}')."
            )
        self.current_state = target_state
        return self.current_state
