"""akaalPipeline.state.lifecycle
===============================
Migration, attempt, and schedule lifecycle state machines.
"""

from __future__ import annotations

from typing import Set
from akaalPipeline.contracts.enums import AttemptLifecycleState, MigrationLifecycleState, ScheduleLifecycleState
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode

# Allowed Migration Lifecycle transitions:
# DRAFT -> CONFIGURING -> DISCOVERED -> PLANNED -> GOVERNANCE_PENDING -> AUTHORIZED -> INITIALIZED -> ACTIVE -> COMPLETED / FAILED / ARCHIVED
_VALID_MIGRATION_TRANSITIONS: dict[MigrationLifecycleState, Set[MigrationLifecycleState]] = {
    MigrationLifecycleState.DRAFT: {MigrationLifecycleState.CONFIGURING, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.CONFIGURING: {MigrationLifecycleState.DISCOVERED, MigrationLifecycleState.DRAFT, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.DISCOVERED: {MigrationLifecycleState.PLANNED, MigrationLifecycleState.CONFIGURING, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.PLANNED: {MigrationLifecycleState.GOVERNANCE_PENDING, MigrationLifecycleState.AUTHORIZED, MigrationLifecycleState.CONFIGURING, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.GOVERNANCE_PENDING: {MigrationLifecycleState.AUTHORIZED, MigrationLifecycleState.PLANNED, MigrationLifecycleState.FAILED, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.AUTHORIZED: {MigrationLifecycleState.INITIALIZED, MigrationLifecycleState.CONFIGURING, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.INITIALIZED: {MigrationLifecycleState.ACTIVE, MigrationLifecycleState.FAILED, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.ACTIVE: {MigrationLifecycleState.COMPLETED, MigrationLifecycleState.FAILED, MigrationLifecycleState.INITIALIZED, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.COMPLETED: {MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.FAILED: {MigrationLifecycleState.INITIALIZED, MigrationLifecycleState.CONFIGURING, MigrationLifecycleState.ARCHIVED},
    MigrationLifecycleState.ARCHIVED: set(),
}

# Allowed Attempt Lifecycle transitions:
_VALID_ATTEMPT_TRANSITIONS: dict[AttemptLifecycleState, Set[AttemptLifecycleState]] = {
    AttemptLifecycleState.REQUESTED: {AttemptLifecycleState.ADMITTED, AttemptLifecycleState.FAILED, AttemptLifecycleState.CANCELLED},
    AttemptLifecycleState.ADMITTED: {AttemptLifecycleState.LEASED, AttemptLifecycleState.FAILED, AttemptLifecycleState.CANCELLED},
    AttemptLifecycleState.LEASED: {AttemptLifecycleState.DISPATCHED, AttemptLifecycleState.FAILED, AttemptLifecycleState.CANCELLED},
    AttemptLifecycleState.DISPATCHED: {AttemptLifecycleState.RUNNING, AttemptLifecycleState.FAILED, AttemptLifecycleState.CANCELLED},
    AttemptLifecycleState.RUNNING: {AttemptLifecycleState.PAUSING, AttemptLifecycleState.RECOVERING, AttemptLifecycleState.COMPLETED, AttemptLifecycleState.FAILED, AttemptLifecycleState.CANCELLED},
    AttemptLifecycleState.PAUSING: {AttemptLifecycleState.PAUSED, AttemptLifecycleState.FAILED, AttemptLifecycleState.CANCELLED},
    AttemptLifecycleState.PAUSED: {AttemptLifecycleState.RUNNING, AttemptLifecycleState.CANCELLED, AttemptLifecycleState.FAILED},
    AttemptLifecycleState.RECOVERING: {AttemptLifecycleState.RUNNING, AttemptLifecycleState.FAILED, AttemptLifecycleState.CANCELLED, AttemptLifecycleState.COMPENSATING},
    AttemptLifecycleState.COMPLETED: set(),
    AttemptLifecycleState.FAILED: {AttemptLifecycleState.RECOVERING, AttemptLifecycleState.COMPENSATING},
    AttemptLifecycleState.CANCELLED: {AttemptLifecycleState.COMPENSATING},
    AttemptLifecycleState.COMPENSATING: {AttemptLifecycleState.COMPENSATED, AttemptLifecycleState.FAILED},
    AttemptLifecycleState.COMPENSATED: set(),
}

# Allowed Schedule Lifecycle transitions:
_VALID_SCHEDULE_TRANSITIONS: dict[ScheduleLifecycleState, Set[ScheduleLifecycleState]] = {
    ScheduleLifecycleState.DRAFT: {ScheduleLifecycleState.VALIDATED, ScheduleLifecycleState.CANCELLED},
    ScheduleLifecycleState.VALIDATED: {ScheduleLifecycleState.ARMED, ScheduleLifecycleState.INVALIDATED, ScheduleLifecycleState.CANCELLED},
    ScheduleLifecycleState.ARMED: {ScheduleLifecycleState.ACTIVATING, ScheduleLifecycleState.INVALIDATED, ScheduleLifecycleState.CANCELLED},
    ScheduleLifecycleState.ACTIVATING: {ScheduleLifecycleState.CONSUMED, ScheduleLifecycleState.ARMED, ScheduleLifecycleState.INVALIDATED, ScheduleLifecycleState.CANCELLED},
    ScheduleLifecycleState.CONSUMED: set(),
    ScheduleLifecycleState.CANCELLED: set(),
    ScheduleLifecycleState.INVALIDATED: {ScheduleLifecycleState.DRAFT, ScheduleLifecycleState.CANCELLED},
}


class MigrationLifecycleMachine:
    @staticmethod
    def validate_transition(from_state: MigrationLifecycleState, to_state: MigrationLifecycleState) -> None:
        if from_state == to_state:
            return
        allowed = _VALID_MIGRATION_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise PipelineError(
                PipelineErrorCode.INVALID_TRANSITION,
                f"Illegal migration lifecycle transition from {from_state.value!r} to {to_state.value!r}.",
            )


class AttemptLifecycleMachine:
    @staticmethod
    def validate_transition(from_state: AttemptLifecycleState, to_state: AttemptLifecycleState) -> None:
        if from_state == to_state:
            return
        allowed = _VALID_ATTEMPT_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise PipelineError(
                PipelineErrorCode.INVALID_TRANSITION,
                f"Illegal attempt lifecycle transition from {from_state.value!r} to {to_state.value!r}.",
            )


class ScheduleLifecycleMachine:
    @staticmethod
    def validate_transition(from_state: ScheduleLifecycleState, to_state: ScheduleLifecycleState) -> None:
        if from_state == to_state:
            return
        allowed = _VALID_SCHEDULE_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise PipelineError(
                PipelineErrorCode.INVALID_TRANSITION,
                f"Illegal schedule lifecycle transition from {from_state.value!r} to {to_state.value!r}.",
            )
