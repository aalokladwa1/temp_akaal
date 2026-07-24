"""Reliability Lifecycle States, Transition Validator, and ReliabilityStateMachine."""

import time
import threading
from enum import Enum
from typing import Dict, List, Set, Tuple, Optional


class ReliabilityState(str, Enum):
    HEALTHY = "Healthy"
    WARNING = "Warning"
    DEGRADED = "Degraded"
    RECOVERING = "Recovering"
    RECOVERED = "Recovered"
    FAILED = "Failed"
    DISASTER = "Disaster"
    OFFLINE = "Offline"


class StateTransitionValidator:
    """Validates allowed state transitions and detects illegal state jumps."""

    ALLOWED_TRANSITIONS: Dict[ReliabilityState, Set[ReliabilityState]] = {
        ReliabilityState.HEALTHY: {ReliabilityState.WARNING, ReliabilityState.DEGRADED, ReliabilityState.FAILED, ReliabilityState.OFFLINE},
        ReliabilityState.WARNING: {ReliabilityState.HEALTHY, ReliabilityState.DEGRADED, ReliabilityState.FAILED},
        ReliabilityState.DEGRADED: {ReliabilityState.HEALTHY, ReliabilityState.RECOVERING, ReliabilityState.FAILED, ReliabilityState.DISASTER},
        ReliabilityState.RECOVERING: {ReliabilityState.RECOVERED, ReliabilityState.FAILED, ReliabilityState.DISASTER},
        ReliabilityState.RECOVERED: {ReliabilityState.HEALTHY, ReliabilityState.WARNING},
        ReliabilityState.FAILED: {ReliabilityState.RECOVERING, ReliabilityState.DISASTER, ReliabilityState.OFFLINE},
        ReliabilityState.DISASTER: {ReliabilityState.RECOVERING, ReliabilityState.OFFLINE},
        ReliabilityState.OFFLINE: {ReliabilityState.RECOVERING, ReliabilityState.HEALTHY},
    }

    def validate_transition(self, current: ReliabilityState, target: ReliabilityState) -> bool:
        allowed = self.ALLOWED_TRANSITIONS.get(current, set())
        return target in allowed


class ReliabilityStateMachine:
    """Enterprise state machine managing reliability lifecycle states and transition logs."""

    def __init__(self, initial_state: ReliabilityState = ReliabilityState.HEALTHY):
        self.current_state = initial_state
        self.validator = StateTransitionValidator()
        self.history: List[Tuple[float, ReliabilityState, ReliabilityState, str]] = []
        self._lock = threading.RLock()

    def transition_to(self, target_state: ReliabilityState, reason: str = "System evaluation") -> bool:
        with self._lock:
            if not self.validator.validate_transition(self.current_state, target_state):
                return False
            old_state = self.current_state
            self.current_state = target_state
            self.history.append((time.time(), old_state, target_state, reason))
            return True

    def get_current_state(self) -> ReliabilityState:
        with self._lock:
            return self.current_state

    def get_history(self) -> List[Tuple[float, ReliabilityState, ReliabilityState, str]]:
        with self._lock:
            return list(self.history)
