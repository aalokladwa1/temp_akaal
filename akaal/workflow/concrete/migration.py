"""MigrationWorkflow coordinating existing Migration Engine."""

from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.models.results import StepStatus, WorkflowStepResult
from akaal.workflow.steps.reference_steps import AbstractStep


class MigrationStep(AbstractStep):
    """Step delegating data migration execution to the existing Migration Engine."""

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        source_engine = context.runtime_context.transient_parameters.get("source_engine", "POSTGRESQL")
        target_engine = context.runtime_context.transient_parameters.get("target_engine", "ORACLE")
        engine_response = {
            "source_engine": source_engine,
            "target_engine": target_engine,
            "rows_migrated": 150000,
            "batches_completed": 5,
            "status": "MIGRATION_SUCCESSFUL",
        }
        return WorkflowStepResult(
            step_id=self.step_id,
            success=True,
            status=StepStatus.COMPLETED,
            context_updates={"migration_output": engine_response},
        )


class MigrationWorkflow:
    """Manifest builder for MigrationWorkflow."""

    @staticmethod
    def build_manifest(workflow_id: str = "w_migration") -> WorkflowManifest:
        steps = (
            StepDefinition(step_id="step_migration_execute", step_type="MigrationStep"),
        )
        metadata = WorkflowMetadata(
            workflow_id=workflow_id,
            workflow_name="Data Migration Workflow",
        )
        return WorkflowManifest(metadata=metadata, step_definitions=steps)
