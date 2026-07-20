"""Workflow Domain Event Definitions."""

from dataclasses import dataclass, field
from typing import Any, Mapping
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class WorkflowEvent:
    """Base immutable domain event emitted by the Workflow Platform."""

    event_id: str
    event_type: str
    workflow_id: str
    timestamp: str = "2026-01-01T00:00:00+00:00"
    payload: Mapping[str, Any] = field(default_factory=dict)
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class WorkflowStateChangedEvent(WorkflowEvent):
    """Event emitted when the workflow state machine transitions to a new state."""
    pass


@dataclass(frozen=True, slots=True)
class StepExecutedEvent(WorkflowEvent):
    """Event emitted when a workflow step completes or fails execution."""
    pass


@dataclass(frozen=True, slots=True)
class WorkflowStartedEvent(WorkflowEvent):
    """Event emitted when workflow execution starts."""
    pass


@dataclass(frozen=True, slots=True)
class WorkflowCompletedEvent(WorkflowEvent):
    """Event emitted when workflow execution completes successfully."""
    pass


@dataclass(frozen=True, slots=True)
class WorkflowFailedEvent(WorkflowEvent):
    """Event emitted when workflow execution fails terminally."""
    pass


@dataclass(frozen=True, slots=True)
class WorkflowRetryingEvent(WorkflowEvent):
    """Event emitted before a step or workflow retry attempt."""
    pass


@dataclass(frozen=True, slots=True)
class WorkflowPausedEvent(WorkflowEvent):
    """Event emitted when a workflow pauses for approval or intervention."""
    pass


@dataclass(frozen=True, slots=True)
class WorkflowCancelledEvent(WorkflowEvent):
    """Event emitted when a workflow execution is cancelled."""
    pass


@dataclass(frozen=True, slots=True)
class ApprovalRequestedEvent(WorkflowEvent):
    """Event emitted when an approval request is created."""
    pass


@dataclass(frozen=True, slots=True)
class ApprovalGrantedEvent(WorkflowEvent):
    """Event emitted when an approval request is granted."""
    pass


@dataclass(frozen=True, slots=True)
class ApprovalRejectedEvent(WorkflowEvent):
    """Event emitted when an approval request is rejected."""
    pass
