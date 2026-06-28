"""
NexusForge — Workflow Engine (State Machine)
=============================================
Implements the deterministic state machine for migration workflow transitions.

TRD Section 13 — Manager State Machine:
  Idle → Project Created → Discovery Started → Discovery Validated
  → GB Loading → GB Validation → Human Approval Pending
  → Production Migration → Production Validation
  → CDC Synchronization → Migration Completed

  Any failure → Recovery State → Checkpoint Restore → Retry

Rules:
  - Transitions are validated — only defined transitions are allowed
  - Skipping states is FORBIDDEN
  - Every transition is logged
  - Failed validations trigger recovery, not skipping
"""

import logging
from typing import Dict, FrozenSet, Optional, Set

from akaal.core.models.enums import WorkflowState

logger = logging.getLogger("nexusforge.workflow_engine")


# ---------------------------------------------------------------------------
# Allowed Transitions Map
# Defines what state transitions are legal.
# This is the guard against unauthorized workflow skipping.
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: Dict[WorkflowState, FrozenSet[WorkflowState]] = {
    WorkflowState.IDLE: frozenset({
        WorkflowState.PROJECT_CREATED,
    }),
    WorkflowState.PROJECT_CREATED: frozenset({
        WorkflowState.DISCOVERY_STARTED,
        WorkflowState.CANCELLED,
    }),
    WorkflowState.DISCOVERY_STARTED: frozenset({
        WorkflowState.DISCOVERY_COMPLETED,
        WorkflowState.FAILED,
        WorkflowState.PAUSED,
    }),
    WorkflowState.DISCOVERY_COMPLETED: frozenset({
        WorkflowState.DISCOVERY_VALIDATED,
        WorkflowState.FAILED,
    }),
    WorkflowState.DISCOVERY_VALIDATED: frozenset({
        WorkflowState.GB_LOADING,
        WorkflowState.FAILED,
    }),
    WorkflowState.GB_LOADING: frozenset({
        WorkflowState.GB_LOADED,
        WorkflowState.FAILED,
        WorkflowState.PAUSED,
    }),
    WorkflowState.GB_LOADED: frozenset({
        WorkflowState.GB_VALIDATION,
        WorkflowState.FAILED,
    }),
    WorkflowState.GB_VALIDATION: frozenset({
        WorkflowState.GB_VALIDATED,
        WorkflowState.FAILED,
    }),
    WorkflowState.GB_VALIDATED: frozenset({
        WorkflowState.HUMAN_APPROVAL_PENDING,
    }),
    WorkflowState.HUMAN_APPROVAL_PENDING: frozenset({
        WorkflowState.HUMAN_APPROVED,
        WorkflowState.PAUSED,
        WorkflowState.CANCELLED,
        WorkflowState.FAILED,
    }),
    WorkflowState.HUMAN_APPROVED: frozenset({
        WorkflowState.PRODUCTION_MIGRATION,
    }),
    WorkflowState.PRODUCTION_MIGRATION: frozenset({
        WorkflowState.PRODUCTION_VALIDATION,
        WorkflowState.FAILED,
        WorkflowState.PAUSED,
    }),
    WorkflowState.PRODUCTION_VALIDATION: frozenset({
        WorkflowState.CDC_SYNCHRONIZATION,
        WorkflowState.FAILED,
    }),
    WorkflowState.CDC_SYNCHRONIZATION: frozenset({
        WorkflowState.MIGRATION_COMPLETED,
        WorkflowState.FAILED,
    }),
    WorkflowState.MIGRATION_COMPLETED: frozenset(),  # Terminal — no further transitions

    # Recovery states — can transition back to retry or escalate
    WorkflowState.FAILED: frozenset({
        WorkflowState.RECOVERY_STARTED,
        WorkflowState.CANCELLED,
        WorkflowState.ESCALATED,
    }),
    WorkflowState.RECOVERY_STARTED: frozenset({
        WorkflowState.CHECKPOINT_RESTORE,
        WorkflowState.ESCALATED,
        WorkflowState.CANCELLED,
    }),
    WorkflowState.CHECKPOINT_RESTORE: frozenset({
        WorkflowState.RETRYING,
        WorkflowState.ESCALATED,
    }),
    WorkflowState.RETRYING: frozenset({
        WorkflowState.DISCOVERY_STARTED,
        WorkflowState.GB_LOADING,
        WorkflowState.PRODUCTION_MIGRATION,
        WorkflowState.CDC_SYNCHRONIZATION,
        WorkflowState.FAILED,
        WorkflowState.ESCALATED,
    }),
    WorkflowState.PAUSED: frozenset({
        WorkflowState.DISCOVERY_STARTED,
        WorkflowState.GB_LOADING,
        WorkflowState.HUMAN_APPROVAL_PENDING,
        WorkflowState.PRODUCTION_MIGRATION,
        WorkflowState.CANCELLED,
    }),
    WorkflowState.ESCALATED: frozenset(),   # Terminal
    WorkflowState.CANCELLED: frozenset(),   # Terminal
}

# Terminal states — no further workflow execution
TERMINAL_STATES: FrozenSet[WorkflowState] = frozenset({
    WorkflowState.MIGRATION_COMPLETED,
    WorkflowState.ESCALATED,
    WorkflowState.CANCELLED,
})


# ---------------------------------------------------------------------------
# Transition Error
# ---------------------------------------------------------------------------

class InvalidTransitionError(Exception):
    """Raised when an illegal workflow state transition is attempted."""
    def __init__(self, from_state: WorkflowState, to_state: WorkflowState) -> None:
        super().__init__(
            f"Invalid transition: {from_state.value} → {to_state.value}. "
            f"Allowed from {from_state.value}: "
            f"{[s.value for s in ALLOWED_TRANSITIONS.get(from_state, frozenset())]}"
        )
        self.from_state = from_state
        self.to_state = to_state


# ---------------------------------------------------------------------------
# Workflow Engine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """
    Deterministic state machine for NexusForge migration workflows.

    The engine validates every state transition before applying it.
    Illegal transitions raise InvalidTransitionError immediately.
    No skipping, no bypassing.
    """

    def __init__(self) -> None:
        logger.info("[WorkflowEngine] Initialized with %d state rules.", len(ALLOWED_TRANSITIONS))

    def validate_transition(
        self,
        current_state: WorkflowState,
        target_state: WorkflowState,
    ) -> bool:
        """
        Check if a transition is allowed without applying it.
        Returns True if allowed, False if forbidden.
        """
        allowed = ALLOWED_TRANSITIONS.get(current_state, frozenset())
        return target_state in allowed

    def transition(
        self,
        current_state: WorkflowState,
        target_state: WorkflowState,
        project_id: str,
        reason: str = "",
    ) -> WorkflowState:
        """
        Validate and apply a state transition.

        Raises InvalidTransitionError if the transition is not allowed.
        Returns the new state on success.
        """
        if current_state in TERMINAL_STATES:
            raise InvalidTransitionError(current_state, target_state)

        allowed = ALLOWED_TRANSITIONS.get(current_state, frozenset())
        if target_state not in allowed:
            logger.error(
                "[WorkflowEngine] ILLEGAL TRANSITION: %s → %s (project=%s). "
                "Allowed: %s",
                current_state.value, target_state.value, project_id,
                [s.value for s in allowed]
            )
            raise InvalidTransitionError(current_state, target_state)

        logger.info(
            "[WorkflowEngine] Transition: %s → %s (project=%s, reason=%s)",
            current_state.value, target_state.value, project_id, reason or "no reason"
        )
        return target_state

    def is_terminal(self, state: WorkflowState) -> bool:
        """Return True if state is a terminal (no-exit) state."""
        return state in TERMINAL_STATES

    def get_allowed_next_states(self, current_state: WorkflowState) -> Set[WorkflowState]:
        """Return the set of valid next states from current_state."""
        return set(ALLOWED_TRANSITIONS.get(current_state, frozenset()))

    def requires_human_approval(self, current_state: WorkflowState) -> bool:
        """Return True if current state requires human approval before proceeding."""
        return current_state == WorkflowState.HUMAN_APPROVAL_PENDING

    def is_in_recovery(self, current_state: WorkflowState) -> bool:
        """Return True if the workflow is in a recovery cycle."""
        return current_state in (
            WorkflowState.FAILED,
            WorkflowState.RECOVERY_STARTED,
            WorkflowState.CHECKPOINT_RESTORE,
            WorkflowState.RETRYING,
        )

    def describe_transition(
        self,
        from_state: WorkflowState,
        to_state: WorkflowState,
    ) -> str:
        """Return a human-readable description of a transition."""
        descriptions = {
            (WorkflowState.IDLE, WorkflowState.PROJECT_CREATED):
                "New migration project initialized",
            (WorkflowState.PROJECT_CREATED, WorkflowState.DISCOVERY_STARTED):
                "Scout agent assigned for source discovery",
            (WorkflowState.DISCOVERY_STARTED, WorkflowState.DISCOVERY_COMPLETED):
                "Source discovery completed — Universal JSON generated",
            (WorkflowState.DISCOVERY_COMPLETED, WorkflowState.DISCOVERY_VALIDATED):
                "Discovery output validated by Validator Agent",
            (WorkflowState.DISCOVERY_VALIDATED, WorkflowState.GB_LOADING):
                "Loading validated schema into GB (staging environment)",
            (WorkflowState.GB_LOADED, WorkflowState.GB_VALIDATION):
                "Validator comparing Universal JSON against GB",
            (WorkflowState.GB_VALIDATED, WorkflowState.HUMAN_APPROVAL_PENDING):
                "All automated validations passed — awaiting human approval",
            (WorkflowState.HUMAN_APPROVED, WorkflowState.PRODUCTION_MIGRATION):
                "Human approved — beginning production migration",
            (WorkflowState.PRODUCTION_MIGRATION, WorkflowState.PRODUCTION_VALIDATION):
                "Production migration complete — validating target",
            (WorkflowState.PRODUCTION_VALIDATION, WorkflowState.CDC_SYNCHRONIZATION):
                "Production validated — starting CDC synchronization",
            (WorkflowState.CDC_SYNCHRONIZATION, WorkflowState.MIGRATION_COMPLETED):
                "CDC synchronization complete — migration successfully finished",
        }
        return descriptions.get(
            (from_state, to_state),
            f"Transition: {from_state.value} → {to_state.value}"
        )
