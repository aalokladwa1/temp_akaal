"""API Gateway REST/gRPC Server Facade."""

import threading
from typing import Any, Dict
from akaal.workflow.api.middleware import SlidingWindowRateLimiter
from akaal.workflow.engine.execution_engine import WorkflowExecutionEngine
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.models.sub_contexts import ExecutionContext


class ApiGatewayServer:
    """REST and gRPC Control Plane Gateway Server."""

    def __init__(
        self,
        engine: WorkflowExecutionEngine | None = None,
        rate_limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        self.engine = engine or WorkflowExecutionEngine()
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter()
        self._lock = threading.Lock()

    def handle_submit_workflow(self, payload: Dict[str, Any], client_id: str = "default") -> Dict[str, Any]:
        """Handle REST/gRPC submit workflow request."""
        allowed, remaining = self.rate_limiter.check_rate_limit(client_id)
        if not allowed:
            return {"status": "ERROR", "message": "Rate limit exceeded"}

        workflow_id = payload.get("workflow_id", "w_api_1")
        context = WorkflowContext(execution_context=ExecutionContext(workflow_id=workflow_id, run_id="api_run_1"))
        manifest = WorkflowManifest(
            metadata=WorkflowMetadata(workflow_id=workflow_id, workflow_name=f"API Workflow {workflow_id}"),
            step_definitions=(StepDefinition(step_id="step_1", step_type="ReferencePassStep"),),
        )

        results = self.engine.submit_and_run_workflow(manifest, context)
        return {
            "workflow_id": workflow_id,
            "status": "COMPLETED" if results["step_1"].success else "FAILED",
            "rate_limit_remaining": remaining,
        }

    def handle_get_status(self, workflow_id: str) -> Dict[str, Any]:
        """Handle REST/gRPC query status request."""
        controller = self.engine.control_plane.get_state_controller(workflow_id)
        if not controller:
            return {"workflow_id": workflow_id, "state": "NOT_FOUND"}
        return {"workflow_id": workflow_id, "state": controller.current_state.name}
