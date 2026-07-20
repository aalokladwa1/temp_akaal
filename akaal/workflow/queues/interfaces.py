"""IWorkflowQueue Protocol and StepExecutionTask Domain DTO."""

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, Tuple
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class StepExecutionTask:
    """Task payload dispatched via workflow queues."""

    task_id: str
    workflow_id: str
    run_id: str
    step_id: str
    step_type: str
    tenant_id: str = "default"
    priority: int = 40
    attempt: int = 1
    parameters: Mapping[str, Any] = field(default_factory=dict)
    enqueued_at: str = "2026-01-01T00:00:00Z"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "step_type": self.step_type,
            "tenant_id": self.tenant_id,
            "priority": self.priority,
            "attempt": self.attempt,
            "parameters": dict(self.parameters),
            "enqueued_at": self.enqueued_at,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "step_type": self.step_type,
            "tenant_id": self.tenant_id,
            "priority": self.priority,
            "attempt": self.attempt,
            "parameters": dict(self.parameters),
            "enqueued_at": self.enqueued_at,
            "checksum": self.checksum,
        }


class IWorkflowQueue(Protocol):
    """Abstract interface decoupling workflow scheduler from queue transports."""

    def enqueue(self, task: StepExecutionTask) -> bool:
        """Enqueue a task payload for execution."""
        ...

    def dequeue(self, visibility_timeout_seconds: float = 30.0) -> Optional[StepExecutionTask]:
        """Dequeue the highest-priority ready task payload."""
        ...

    def acknowledge(self, task_id: str) -> bool:
        """Acknowledge successful execution and remove task from queue."""
        ...

    def dead_letter(self, task_id: str, reason: str) -> bool:
        """Move unrecoverable or poisoned task to dead letter queue."""
        ...

    def size(self) -> int:
        """Return total pending tasks count in queue."""
        ...
