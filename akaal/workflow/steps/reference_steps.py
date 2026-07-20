"""Reference Step Implementations for Contract and Lifecycle Testing."""

from typing import Any, Mapping
from akaal.workflow.interfaces.base import IStep
from akaal.workflow.models.checkpoint import WorkflowCheckpoint
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.results import StepStatus, ValidationResult, WorkflowStepResult


class AbstractStep(IStep):
    """Abstract base step providing default lifecycle implementations."""

    def __init__(self, step_id: str = "abstract-step", **kwargs: Any) -> None:
        self._step_id = step_id
        self.initialized = False
        self.cleaned_up = False
        self.success_hook_called = False
        self.failure_hook_called = False
        self.rolled_back = False

    @property
    def step_id(self) -> str:
        return self._step_id

    def initialize(self, context: WorkflowContext) -> None:
        self.initialized = True

    def validate_preconditions(self, context: WorkflowContext) -> ValidationResult:
        return ValidationResult.success()

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        return WorkflowStepResult(step_id=self.step_id, success=True, status=StepStatus.COMPLETED)

    def on_success(self, context: WorkflowContext, result: WorkflowStepResult) -> None:
        self.success_hook_called = True

    def on_failure(self, context: WorkflowContext, error: Exception) -> None:
        self.failure_hook_called = True

    def validate_postconditions(self, context: WorkflowContext, result: WorkflowStepResult) -> ValidationResult:
        return ValidationResult.success()

    def checkpoint(self, context: WorkflowContext) -> WorkflowCheckpoint:
        return WorkflowCheckpoint(
            checkpoint_id=f"cp-{self.step_id}",
            workflow_id=context.workflow_id,
            run_id=context.run_id,
            step_id=self.step_id,
            state="CHECKPOINTED",
            context=context,
        )

    def resume(self, checkpoint: WorkflowCheckpoint, context: WorkflowContext) -> WorkflowStepResult:
        return self.execute(context)

    def rollback(self, context: WorkflowContext) -> WorkflowStepResult:
        self.rolled_back = True
        return WorkflowStepResult(step_id=self.step_id, success=True, status=StepStatus.ROLLED_BACK)

    def cleanup(self, context: WorkflowContext) -> None:
        self.cleaned_up = True


class ReferencePassStep(AbstractStep):
    """Reference step implementation that executes successfully."""

    def __init__(self, step_id: str = "pass-step", custom_output: str = "ok", **kwargs: Any) -> None:
        super().__init__(step_id=step_id, **kwargs)
        self.custom_output = custom_output

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        return WorkflowStepResult(
            step_id=self.step_id,
            success=True,
            status=StepStatus.COMPLETED,
            duration_ms=10.0,
            context_updates={self.step_id: self.custom_output},
            checkpoint_created=True,
        )


class ReferenceFailStep(AbstractStep):
    """Reference step implementation that fails during execute()."""

    def __init__(self, step_id: str = "fail-step", failure_message: str = "Step failed intentionally", **kwargs: Any) -> None:
        super().__init__(step_id=step_id, **kwargs)
        self.failure_message = failure_message

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        return WorkflowStepResult(
            step_id=self.step_id,
            success=False,
            status=StepStatus.FAILED,
            errors=(self.failure_message,),
            retry_allowed=False,
        )


class ReferencePreconditionFailStep(AbstractStep):
    """Reference step implementation that fails precondition checks."""

    def __init__(self, step_id: str = "pre-fail-step", **kwargs: Any) -> None:
        super().__init__(step_id=step_id, **kwargs)

    def validate_preconditions(self, context: WorkflowContext) -> ValidationResult:
        return ValidationResult.failure(errors=("Precondition check explicitly failed for reference step",))
