"""Execution Records, Telemetry, Trace, and Metrics Models."""

from dataclasses import dataclass, field
from typing import Any, Tuple
from akaal.workflow.models.results import WorkflowStepResult
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class StateTransitionRecord:
    """Immutable audit record of a state machine transition."""

    from_state: str
    to_state: str
    timestamp: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class WorkflowMetrics:
    """Aggregated execution metrics for a workflow run."""

    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    retried_steps: int = 0
    execution_duration_ms: float = 0.0
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "retried_steps": self.retried_steps,
            "execution_duration_ms": self.execution_duration_ms,
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "retried_steps": self.retried_steps,
            "execution_duration_ms": self.execution_duration_ms,
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class WorkflowExecutionTrace:
    """Immutable audit trace of an entire workflow execution lifecycle."""

    run_id: str
    workflow_id: str
    step_results: Tuple[WorkflowStepResult, ...] = field(default_factory=tuple)
    state_transitions: Tuple[StateTransitionRecord, ...] = field(default_factory=tuple)
    start_time: str = "2026-01-01T00:00:00+00:00"
    end_time: str | None = None
    total_duration_ms: float = 0.0
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "step_results": [s.to_dict() for s in self.step_results],
            "state_transitions": [t.to_dict() for t in self.state_transitions],
            "start_time": self.start_time,
            "end_time": self.end_time or "",
            "total_duration_ms": self.total_duration_ms,
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "step_results": [s.to_dict() for s in self.step_results],
            "state_transitions": [t.to_dict() for t in self.state_transitions],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "checksum": self.checksum,
        }
