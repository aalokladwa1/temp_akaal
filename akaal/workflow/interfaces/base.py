"""Core Structural Interfaces and Protocols for AKAAL Workflow Platform."""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from akaal.workflow.models.checkpoint import WorkflowCheckpoint
    from akaal.workflow.models.context import WorkflowContext
    from akaal.workflow.models.results import ValidationResult, WorkflowStepResult


class IStep(Protocol):
    """Generic Step Interface contract. Every workflow step MUST implement this interface."""

    @property
    def step_id(self) -> str:
        """Unique identifier for this step instance."""
        ...

    def initialize(self, context: "WorkflowContext") -> None:
        """Initialize step prior to execution."""
        ...

    def validate_preconditions(self, context: "WorkflowContext") -> "ValidationResult":
        """Validate system and state preconditions prior to executing step logic."""
        ...

    def execute(self, context: "WorkflowContext") -> "WorkflowStepResult":
        """Execute step core business orchestration logic."""
        ...

    def on_success(self, context: "WorkflowContext", result: "WorkflowStepResult") -> None:
        """Lifecycle hook invoked after successful execution and precondition checks."""
        ...

    def on_failure(self, context: "WorkflowContext", error: Exception) -> None:
        """Lifecycle hook invoked after failed execution or precondition check failure."""
        ...

    def validate_postconditions(self, context: "WorkflowContext", result: "WorkflowStepResult") -> "ValidationResult":
        """Validate system invariants and output postconditions following execution."""
        ...

    def checkpoint(self, context: "WorkflowContext") -> "WorkflowCheckpoint":
        """Generate a state snapshot checkpoint for this step."""
        ...

    def resume(self, checkpoint: "WorkflowCheckpoint", context: "WorkflowContext") -> "WorkflowStepResult":
        """Resume step execution from a persisted checkpoint."""
        ...

    def rollback(self, context: "WorkflowContext") -> "WorkflowStepResult":
        """Execute compensating rollback logic for this step."""
        ...

    def cleanup(self, context: "WorkflowContext") -> None:
        """Cleanup temporary resources in a guaranteed finally block."""
        ...


class IExecutionStrategy(Protocol):
    """Abstract strategy interface for executing steps synchronously or asynchronously."""

    def execute_step(self, step: IStep, context: "WorkflowContext") -> "WorkflowStepResult":
        ...


class IEngine(Protocol):
    """Abstract interface for high-level Workflow Engine coordinator."""

    def execute(self, workflow_id: str, parameters: dict[str, Any] | None = None) -> Any:
        ...

    def pause(self, workflow_id: str) -> None:
        ...

    def resume(self, workflow_id: str) -> Any:
        ...

    def cancel(self, workflow_id: str) -> None:
        ...

    def rollback(self, workflow_id: str) -> Any:
        ...


class IWorkflowLock(Protocol):
    """Abstract distributed lock interface for multi-node/multi-threaded workflow coordination."""

    def acquire_lock(self, workflow_id: str, ttl_seconds: int = 30) -> bool:
        """Acquire lock lease for workflow ID."""
        ...

    def release_lock(self, workflow_id: str) -> None:
        """Release lock lease for workflow ID."""
        ...
