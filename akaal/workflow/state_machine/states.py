"""Workflow State Enumeration."""

from enum import Enum


class WorkflowState(str, Enum):
    """Explicit states of the Workflow State Machine."""

    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
