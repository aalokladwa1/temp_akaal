"""
ExecutionLifecycleManager module.
Owns task assignment lifecycle state machine transitions deterministically.
"""

from dataclasses import dataclass, field, replace
from threading import RLock
import logging

from akaal.distributed.domain.identifiers import TaskId, ExecutionId
from akaal.distributed.domain.enums import AssignmentState
from akaal.distributed.domain.models import Assignment
from akaal.distributed.domain.errors import TaskDistributionError
from akaal.distributed.clock.clock import Clock, SystemClock
from akaal.distributed.events.events import EventPublisher

logger = logging.getLogger("nexusforge.distributed.lifecycle")


class ExecutionLifecycleManager:
    """
    State machine manager for task execution assignment lifecycle.
    """

    ALLOWED_TRANSITIONS: Dict[AssignmentState, Set[AssignmentState]] = {
        AssignmentState.QUEUED: {AssignmentState.ASSIGNED, AssignmentState.FAILED},
        AssignmentState.ASSIGNED: {AssignmentState.LEASED, AssignmentState.FAILED},
        AssignmentState.LEASED: {AssignmentState.RUNNING, AssignmentState.FAILED, AssignmentState.RETRY},
        AssignmentState.RUNNING: {AssignmentState.SUCCESS, AssignmentState.FAILED, AssignmentState.RETRY},
        AssignmentState.FAILED: {AssignmentState.RETRY, AssignmentState.COMPLETED},
        AssignmentState.RETRY: {AssignmentState.QUEUED, AssignmentState.ASSIGNED, AssignmentState.FAILED},
        AssignmentState.SUCCESS: {AssignmentState.COMPLETED},
        AssignmentState.COMPLETED: set(),
    }

    def __init__(self, publisher: EventPublisher, clock: Optional[Clock] = None) -> None:
        self._lock = RLock()
        self._publisher = publisher
        self._clock = clock or SystemClock()

    def validate_transition(self, current: AssignmentState, target: AssignmentState) -> None:
        """Validate if lifecycle transition is legal."""
        if current == target:
            return
        allowed = self.ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise TaskDistributionError(
                f"Illegal task assignment state transition: {current.value} -> {target.value}"
            )

    def transition_assignment(self, assignment: Assignment, target_state: AssignmentState) -> Assignment:
        """Validates and returns updated Assignment dataclass."""
        with self._lock:
            self.validate_transition(assignment.state, target_state)
            return replace(assignment, state=target_state)
