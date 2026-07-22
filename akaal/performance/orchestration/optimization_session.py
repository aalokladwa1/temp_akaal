"""
Optimization State Machine and Session Model.
"""

from enum import Enum
from datetime import datetime, timezone
import uuid
from typing import Dict, Any, List, Optional
from threading import RLock

from akaal.performance.failures.classification import PerformanceEngineError, PerformanceFailureType


class OptimizationState(str, Enum):
    CREATED = "Created"
    BASELINE_CAPTURED = "BaselineCaptured"
    ANALYZING = "Analyzing"
    RULES_EVALUATED = "RulesEvaluated"
    WAITING_APPROVAL = "WaitingApproval"
    EXECUTING = "Executing"
    VALIDATING = "Validating"
    COMPLETED = "Completed"
    ROLLED_BACK = "RolledBack"
    FAILED = "Failed"


class OptimizationSession:
    """Represents a single deterministic, auditable execution run of performance optimization."""

    # Valid transitions from each state
    _VALID_TRANSITIONS: Dict[OptimizationState, List[OptimizationState]] = {
        OptimizationState.CREATED: [OptimizationState.BASELINE_CAPTURED, OptimizationState.FAILED],
        OptimizationState.BASELINE_CAPTURED: [OptimizationState.ANALYZING, OptimizationState.FAILED],
        OptimizationState.ANALYZING: [OptimizationState.RULES_EVALUATED, OptimizationState.FAILED],
        OptimizationState.RULES_EVALUATED: [OptimizationState.EXECUTING, OptimizationState.WAITING_APPROVAL, OptimizationState.COMPLETED, OptimizationState.FAILED],
        OptimizationState.WAITING_APPROVAL: [OptimizationState.EXECUTING, OptimizationState.FAILED],
        OptimizationState.EXECUTING: [OptimizationState.VALIDATING, OptimizationState.FAILED],
        OptimizationState.VALIDATING: [OptimizationState.COMPLETED, OptimizationState.ROLLED_BACK, OptimizationState.FAILED],
        OptimizationState.COMPLETED: [],
        OptimizationState.ROLLED_BACK: [],
        OptimizationState.FAILED: []
    }

    def __init__(self, run_mode: str = "Auto") -> None:
        self._lock = RLock()
        self.session_id = f"opt_sess_{uuid.uuid4().hex[:12]}"
        self.run_mode = run_mode
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.end_time: Optional[str] = None
        self.current_state = OptimizationState.CREATED
        self.state_history: List[Dict[str, Any]] = [
            {"state": OptimizationState.CREATED, "timestamp": self.start_time}
        ]

        # Audit & improvement metrics
        self.collected_metrics: Dict[str, Any] = {}
        self.rules_evaluated: List[str] = []
        self.optimizers_executed: List[str] = []
        self.optimizers_skipped: List[str] = []
        self.rollback_events: List[Dict[str, Any]] = []
        self.baseline_metrics: Dict[str, Any] = {}
        self.final_metrics: Dict[str, Any] = {}
        self.overall_improvement: float = 0.0
        self.status = "ACTIVE"
        self.audit_info: Dict[str, Any] = {}

        # Recorded asset versions
        self.profile_version = "1.0"
        self.rule_version = "1.0"
        self.policy_version = "1.0"
        self.plugin_version = "1.0"
        self.benchmark_version = "1.0"

    def transition_to(self, target_state: OptimizationState, reason: str = "") -> None:
        """Validates and executes lifecycle state transition."""
        with self._lock:
            allowed = self._VALID_TRANSITIONS.get(self.current_state, [])
            if target_state not in allowed:
                raise PerformanceEngineError(
                    PerformanceFailureType.RULE_CONFLICT,
                    f"Invalid state transition from '{self.current_state.value}' to '{target_state.value}'."
                )
            
            self.current_state = target_state
            ts = datetime.now(timezone.utc).isoformat()
            self.state_history.append({"state": target_state, "timestamp": ts, "reason": reason})

            if target_state in (OptimizationState.COMPLETED, OptimizationState.ROLLED_BACK, OptimizationState.FAILED):
                self.end_time = ts
                self.status = target_state.value
