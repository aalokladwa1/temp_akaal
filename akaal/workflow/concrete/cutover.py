"""CutoverWorkflow orchestrating CDC Stop -> Final Sync -> Cutover Switch."""

from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.models.results import StepStatus, WorkflowStepResult
from akaal.workflow.steps.reference_steps import AbstractStep


class CdcStopStep(AbstractStep):
    """Step stopping CDC change capture stream gracefully."""

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        cdc_result = {
            "cdc_stream_status": "STOPPED",
            "last_captured_lsn": "0/16B3D48",
            "unprocessed_events": 0,
        }
        return WorkflowStepResult(
            step_id=self.step_id,
            success=True,
            status=StepStatus.COMPLETED,
            context_updates={"cdc_stop_output": cdc_result},
        )


class FinalSyncStep(AbstractStep):
    """Step executing final change data synchronization catch-up."""

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        sync_result = {
            "sync_status": "FINAL_SYNC_COMPLETE",
            "lag_seconds": 0.0,
        }
        return WorkflowStepResult(
            step_id=self.step_id,
            success=True,
            status=StepStatus.COMPLETED,
            context_updates={"final_sync_output": sync_result},
        )


class CutoverSwitchStep(AbstractStep):
    """Step executing application connection switch to target database."""

    def execute(self, context: WorkflowContext) -> WorkflowStepResult:
        cutover_result = {
            "dns_switch_status": "COMPLETED",
            "target_active": True,
            "source_read_only": True,
        }
        return WorkflowStepResult(
            step_id=self.step_id,
            success=True,
            status=StepStatus.COMPLETED,
            context_updates={"cutover_switch_output": cutover_result},
        )


class CutoverWorkflow:
    """Manifest builder for CutoverWorkflow."""

    @staticmethod
    def build_manifest(workflow_id: str = "w_cutover") -> WorkflowManifest:
        steps = (
            StepDefinition(step_id="step_cdc_stop", step_type="CdcStopStep"),
            StepDefinition(step_id="step_final_sync", step_type="FinalSyncStep", dependencies=("step_cdc_stop",)),
            StepDefinition(step_id="step_cutover_switch", step_type="CutoverSwitchStep", dependencies=("step_final_sync",)),
        )
        metadata = WorkflowMetadata(
            workflow_id=workflow_id,
            workflow_name="Cutover Orchestration Workflow",
        )
        return WorkflowManifest(metadata=metadata, step_definitions=steps)
