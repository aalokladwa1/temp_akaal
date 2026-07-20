"""ExecutionPipeline orchestrating the full IStep lifecycle with success/failure branching."""

import time
from typing import Tuple
from akaal.workflow.exceptions import (
    PostconditionFailedException,
    PreconditionFailedException,
    StepExecutionException,
    StepRetryExhaustedException,
    StepTimeoutException,
)
from akaal.workflow.execution.policies import (
    FixedTimeoutPolicy,
    IRetryPolicy,
    ITimeoutPolicy,
    NoRetryPolicy,
)
from akaal.workflow.interfaces.base import IStep
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.results import StepStatus, WorkflowStepResult
from akaal.workflow.utils.clock import IClock, SystemClock


class ExecutionPipeline:
    """Pipeline orchestrator enforcing step lifecycle hooks and error compensation."""

    def __init__(
        self,
        clock: IClock | None = None,
        retry_policy: IRetryPolicy | None = None,
        timeout_policy: ITimeoutPolicy | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._retry_policy = retry_policy or NoRetryPolicy()
        self._timeout_policy = timeout_policy or FixedTimeoutPolicy()

    def run_pipeline(
        self,
        step: IStep,
        context: WorkflowContext,
        timeout_seconds: float = 300.0,
        max_retries: int = 3,
        retry_policy: IRetryPolicy | None = None,
        timeout_policy: ITimeoutPolicy | None = None,
    ) -> Tuple[WorkflowStepResult, WorkflowContext]:
        """Execute complete step lifecycle:
        initialize -> validate_preconditions -> execute -> on_success/on_failure -> validate_postconditions -> checkpoint -> cleanup
        """
        active_retry_policy = retry_policy or self._retry_policy
        active_timeout_policy = timeout_policy or self._timeout_policy

        start_time = self._clock.monotonic()
        updated_context = context

        try:
            # 1. Initialize
            step.initialize(updated_context)

            # 2. Validate Preconditions
            pre_result = step.validate_preconditions(updated_context)
            if not pre_result.valid:
                err_msg = "; ".join(pre_result.errors) if pre_result.errors else "Precondition check failed"
                raise PreconditionFailedException(step.step_id, err_msg)

            # 3. Execute step logic under timeout & retry policies
            result = self._execute_with_retry_and_timeout(
                step=step,
                context=updated_context,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                retry_policy=active_retry_policy,
                timeout_policy=active_timeout_policy,
            )

            if not result.success:
                raise StepExecutionException(
                    step_id=step.step_id,
                    message="; ".join(result.errors) if result.errors else "Step reported failure",
                )

            # 4. Successful Execution Hook
            step.on_success(updated_context, result)

            # 5. Validate Postconditions
            post_result = step.validate_postconditions(updated_context, result)
            if not post_result.valid:
                err_msg = "; ".join(post_result.errors) if post_result.errors else "Postcondition check failed"
                raise PostconditionFailedException(step.step_id, err_msg)

            # 6. Checkpoint step state if requested
            if result.checkpoint_created:
                step.checkpoint(updated_context)

            # Update context with step updates
            if result.context_updates:
                updated_context = updated_context.with_updates(
                    runtime_updates={"temporary_state": result.context_updates}
                )

            duration = (self._clock.monotonic() - start_time) * 1000.0
            final_result = WorkflowStepResult(
                step_id=result.step_id,
                success=True,
                status=StepStatus.COMPLETED,
                duration_ms=duration,
                warnings=result.warnings,
                errors=result.errors,
                metrics=result.metrics,
                artifacts=result.artifacts,
                context_updates=result.context_updates,
                checkpoint_created=result.checkpoint_created,
                next_step_override=result.next_step_override,
                retry_allowed=result.retry_allowed,
            )
            return final_result, updated_context

        except Exception as exc:
            # Failure Branch
            step.on_failure(updated_context, exc)
            
            # Execute Rollback
            rollback_res = step.rollback(updated_context)

            duration = (self._clock.monotonic() - start_time) * 1000.0
            error_msg = str(exc)
            
            failure_result = WorkflowStepResult(
                step_id=step.step_id,
                success=False,
                status=StepStatus.FAILED if not rollback_res.success else StepStatus.ROLLED_BACK,
                duration_ms=duration,
                warnings=rollback_res.warnings,
                errors=(error_msg,),
                metrics=rollback_res.metrics,
                artifacts=rollback_res.artifacts,
                context_updates=rollback_res.context_updates,
                checkpoint_created=False,
                retry_allowed=False,
            )
            return failure_result, updated_context

        finally:
            # 7. Guaranteed Cleanup
            step.cleanup(updated_context)

    def _execute_with_retry_and_timeout(
        self,
        step: IStep,
        context: WorkflowContext,
        timeout_seconds: float,
        max_retries: int,
        retry_policy: IRetryPolicy,
        timeout_policy: ITimeoutPolicy,
    ) -> WorkflowStepResult:
        """Helper executing step under timeout and retry policy."""
        attempt = 0
        last_exception: Exception | None = None

        while True:
            attempt += 1
            try:
                def call_step() -> WorkflowStepResult:
                    return step.execute(context)

                result = timeout_policy.execute_with_timeout(call_step, timeout_seconds=timeout_seconds)
                if result.success:
                    return result

                last_exception = StepExecutionException(step.step_id, "; ".join(result.errors))
                if not result.retry_allowed or not retry_policy.should_retry(attempt, max_retries, last_exception):
                    return result

            except TimeoutError as err:
                last_exception = StepTimeoutException(step.step_id, timeout_seconds)
                if not retry_policy.should_retry(attempt, max_retries, last_exception):
                    raise last_exception from err
            except Exception as err:
                last_exception = err
                if not retry_policy.should_retry(attempt, max_retries, err):
                    raise err

            # Delay before next attempt
            delay = retry_policy.get_delay_seconds(attempt)
            if delay > 0:
                time.sleep(delay)
