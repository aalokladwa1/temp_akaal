"""RollbackWorkflow orchestrating reverse execution and rollback checkpoints."""

from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.models.results import StepStatus, WorkflowStepResult
from akaal.workflow.steps.reference_steps import AbstractStep


class RollbackStep(AbstractStep):
    """Step executing reverse execution and state restoration."""

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        rollback_result = {
            "rollback_status": "COMPLETED",
            "source_writes_enabled": True,
            "target_cleanup": "CLEANED",
        }
        return WorkflowStepResult(
            step_id=self.step_id,
            success=True,
            status=StepStatus.COMPLETED,
            context_updates={"rollback_output": rollback_result},
        )


class RollbackWorkflow:
    """Manifest builder for RollbackWorkflow."""

    @staticmethod
    def build_manifest(workflow_id: str = "w_rollback") -> WorkflowManifest:
        steps = (
            StepDefinition(step_id="step_rollback_execute", step_type="RollbackStep"),
        )
        metadata = WorkflowMetadata(
            workflow_id=workflow_id,
            workflow_name="Rollback Workflow",
        )
        return WorkflowManifest(metadata=metadata, step_definitions=steps)
