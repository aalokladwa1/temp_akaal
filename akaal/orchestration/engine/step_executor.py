"""
StepExecutor component.
Executes individual WorkflowStep instances within WorkflowContext and handles exceptions.
"""

from typing import Dict, Any
import logging
import time

from akaal.orchestration.workflow.step import WorkflowStep
from akaal.orchestration.workflow.context import WorkflowContext
from akaal.orchestration.domain.errors import WorkflowExecutionError
from akaal.orchestration.events.events import StepStarted, StepCompleted

logger = logging.getLogger("nexusforge.orchestration.step_executor")


class StepExecutor:
    """
    Executes WorkflowStep lifecycle methods.
    """

    def execute_step(self, step: WorkflowStep, context: WorkflowContext, step_index: int = 0) -> Dict[str, Any]:
        """
        Executes a WorkflowStep through its lifecycle:
        initialize() -> validate() -> execute() -> cleanup()
        """
        w_id = str(context.job.workflow_id)
        context.publisher.publish(
            StepStarted(
                aggregate_id=w_id,
                workflow_id=w_id,
                step_name=step.name,
                step_index=step_index,
            )
        )

        start_time = time.time()
        try:
            # 1. Initialize
            step.initialize(context)

            # 2. Validate
            if not step.validate(context):
                raise WorkflowExecutionError(f"Step '{step.name}' precondition validation failed.")

            # Check cancellation
            if context.cancellation_token.is_cancelled:
                raise WorkflowExecutionError(f"Step '{step.name}' execution cancelled.")

            # 3. Execute
            output = step.execute(context)
            duration = time.time() - start_time

            context.publisher.publish(
                StepCompleted(
                    aggregate_id=w_id,
                    workflow_id=w_id,
                    step_name=step.name,
                    duration_seconds=duration,
                    output_summary=output,
                )
            )

            return output

        except Exception as e:
            logger.error(f"Step '{step.name}' execution failed: {str(e)}", exc_info=True)
            raise WorkflowExecutionError(f"Step '{step.name}' execution failed: {str(e)}") from e

        finally:
            try:
                step.cleanup(context)
            except Exception as cleanup_err:
                logger.warning(f"Error during step '{step.name}' cleanup: {str(cleanup_err)}")

    def rollback_step(self, step: WorkflowStep, context: WorkflowContext) -> None:
        """Executes step rollback."""
        try:
            step.rollback(context)
        except Exception as e:
            logger.error(f"Error rolling back step '{step.name}': {str(e)}", exc_info=True)
            raise WorkflowExecutionError(f"Rollback failed for step '{step.name}': {str(e)}") from e
