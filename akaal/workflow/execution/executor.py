"""Step Executor and Execution Strategies."""

import asyncio
from typing import Tuple
from akaal.workflow.execution.pipeline import ExecutionPipeline
from akaal.workflow.execution.policies import IRetryPolicy, ITimeoutPolicy
from akaal.workflow.interfaces.base import IExecutionStrategy, IStep
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.results import WorkflowStepResult
from akaal.workflow.utils.clock import IClock, SystemClock


class StepExecutor:
    """Delegates step lifecycle execution to ExecutionPipeline."""

    def __init__(
        self,
        pipeline: ExecutionPipeline | None = None,
        clock: IClock | None = None,
    ) -> None:
        self._pipeline = pipeline or ExecutionPipeline(clock=clock)
        self._clock = clock or SystemClock()

    def execute_step(
        self,
        step: IStep,
        context: WorkflowContext,
        timeout_seconds: float = 300.0,
        max_retries: int = 3,
        retry_policy: IRetryPolicy | None = None,
        timeout_policy: ITimeoutPolicy | None = None,
    ) -> Tuple[WorkflowStepResult, WorkflowContext]:
        """Execute step through ExecutionPipeline."""
        return self._pipeline.run_pipeline(
            step=step,
            context=context,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_policy=retry_policy,
            timeout_policy=timeout_policy,
        )


class SyncExecutionStrategy:
    """Synchronous in-process execution strategy."""

    def __init__(self, executor: StepExecutor | None = None) -> None:
        self._executor = executor or StepExecutor()

    def execute_step(self, step: IStep, context: WorkflowContext) -> WorkflowStepResult:
        result, _ = self._executor.execute_step(step, context)
        return result


class AsyncExecutionStrategy:
    """Asynchronous non-blocking execution strategy."""

    def __init__(self, executor: StepExecutor | None = None) -> None:
        self._executor = executor or StepExecutor()

    async def execute_step_async(self, step: IStep, context: WorkflowContext) -> WorkflowStepResult:
        loop = asyncio.get_event_loop()
        result, _ = await loop.run_in_executor(None, self._executor.execute_step, step, context)
        return result

    def execute_step(self, step: IStep, context: WorkflowContext) -> WorkflowStepResult:
        return asyncio.run(self.execute_step_async(step, context))
