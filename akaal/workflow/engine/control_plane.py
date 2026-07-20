"""Control Plane Engine managing state, scheduling, admission, and outbox."""

import threading
from typing import Dict, Optional
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import WorkflowManifest
from akaal.workflow.planning.planner import ExecutionPlan, ExecutionPlanner
from akaal.workflow.resilience.admission import AdmissionController
from akaal.workflow.scheduling.scheduler import WorkflowScheduler
from akaal.workflow.state_machine.controller import StateController
from akaal.workflow.state_machine.states import WorkflowState


class ControlPlaneEngine:
    """Control Plane coordinator managing state, scheduling decisions, and manifests."""

    def __init__(
        self,
        planner: ExecutionPlanner | None = None,
        scheduler: WorkflowScheduler | None = None,
        admission: AdmissionController | None = None,
    ) -> None:
        self.planner = planner or ExecutionPlanner()
        self.scheduler = scheduler or WorkflowScheduler()
        self.admission = admission or AdmissionController()
        self._state_controllers: Dict[str, StateController] = {}
        self._plans: Dict[str, ExecutionPlan] = {}
        self._lock = threading.Lock()

    def register_and_schedule(
        self,
        manifest: WorkflowManifest,
        context: WorkflowContext,
        tenant_id: str = "default",
        priority: int = 40,
    ) -> ExecutionPlan:
        """Register workflow, build execution plan, and enqueue initial tasks."""
        with self._lock:
            admitted, reason = self.admission.evaluate_request(tenant_id, priority)
            if not admitted:
                raise RuntimeError(reason)

            workflow_id = context.workflow_id
            controller = StateController(initial_state=WorkflowState.CREATED)
            controller.transition_to(WorkflowState.READY)
            controller.transition_to(WorkflowState.RUNNING)
            self._state_controllers[workflow_id] = controller

            plan = self.planner.create_plan(manifest)
            self._plans[workflow_id] = plan

            step_types = {s.step_id: s.step_type for s in manifest.step_definitions}
            self.scheduler.submit_plan(plan, step_types=step_types, tenant_id=tenant_id, priority=priority)
            return plan

    def get_state_controller(self, workflow_id: str) -> Optional[StateController]:
        with self._lock:
            return self._state_controllers.get(workflow_id)
