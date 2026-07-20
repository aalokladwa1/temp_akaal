"""AKAAL CLI Subcommand Handler Functions."""

from typing import Any, Dict
from akaal.workflow.engine.execution_engine import WorkflowExecutionEngine
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.models.sub_contexts import ExecutionContext


class WorkflowCliCommands:
    """Executes CLI subcommand handlers."""

    def __init__(self, engine: WorkflowExecutionEngine | None = None) -> None:
        self.engine = engine or WorkflowExecutionEngine()

    def submit_workflow(self, workflow_id: str, step_type: str = "ReferencePassStep") -> Dict[str, Any]:
        """Submit and run a workflow manifest via CLI."""
        context = WorkflowContext(execution_context=ExecutionContext(workflow_id=workflow_id, run_id="cli_run_1"))
        manifest = WorkflowManifest(
            metadata=WorkflowMetadata(workflow_id=workflow_id, workflow_name=f"CLI Workflow {workflow_id}"),
            step_definitions=(StepDefinition(step_id="step_1", step_type=step_type),),
        )
        results = self.engine.submit_and_run_workflow(manifest, context)
        return {"workflow_id": workflow_id, "status": "COMPLETED" if results["step_1"].success else "FAILED"}

    def get_status(self, workflow_id: str) -> Dict[str, Any]:
        """Fetch current workflow execution state."""
        controller = self.engine.control_plane.get_state_controller(workflow_id)
        if not controller:
            return {"workflow_id": workflow_id, "state": "NOT_FOUND"}
        return {"workflow_id": workflow_id, "state": controller.current_state.name}
