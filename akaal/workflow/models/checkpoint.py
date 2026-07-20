"""Workflow Checkpoint Model for Crash Recovery and Resumable Execution."""

from dataclasses import dataclass, field
from typing import Any, Tuple
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class WorkflowCheckpoint:
    """Immutable state snapshot for resuming workflow execution following pause or crash."""

    checkpoint_id: str
    workflow_id: str
    run_id: str
    step_id: str
    state: str
    context: WorkflowContext
    completed_steps: Tuple[str, ...] = field(default_factory=tuple)
    pending_steps: Tuple[str, ...] = field(default_factory=tuple)
    created_at: str = "2026-01-01T00:00:00+00:00"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        payload = {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "state": self.state,
            "context": self.context.to_dict(),
            "completed_steps": list(self.completed_steps),
            "pending_steps": list(self.pending_steps),
            "created_at": self.created_at,
        }
        object.__setattr__(self, "checksum", compute_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "state": self.state,
            "context": self.context.to_dict(),
            "completed_steps": list(self.completed_steps),
            "pending_steps": list(self.pending_steps),
            "created_at": self.created_at,
            "checksum": self.checksum,
        }
