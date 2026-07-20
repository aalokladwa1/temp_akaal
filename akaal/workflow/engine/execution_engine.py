"""Workflow Execution Engine unifying Control Plane, Data Plane, Planning, and Scheduling."""

import threading
from typing import Dict, Optional
from akaal.workflow.engine.control_plane import ControlPlaneEngine
from akaal.workflow.engine.data_plane import DataPlaneWorker
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.metadata import WorkflowManifest
from akaal.workflow.models.results import StepStatus, WorkflowStepResult
from akaal.workflow.planning.planner import ExecutionPlan
from akaal.workflow.registry.registry import WorkflowStepRegistry
from akaal.workflow.state_machine.states import WorkflowState


class WorkflowExecutionEngine:
    """Central orchestration root driving workflow planning, scheduling, execution, and state transitions."""

    def __init__(
        self,
        control_plane: ControlPlaneEngine | None = None,
        registry: WorkflowStepRegistry | None = None,
    ) -> None:
        self.control_plane = control_plane or ControlPlaneEngine()
        self.registry = registry or WorkflowStepRegistry()
        self.worker = DataPlaneWorker(worker_id="worker_local_1", registry=self.registry)
        self._lock = threading.Lock()

    def submit_and_run_workflow(
        self,
        manifest: WorkflowManifest,
        context: WorkflowContext,
        tenant_id: str = "default",
        priority: int = 40,
    ) -> dict[str, WorkflowStepResult]:
        """Submit a workflow, build multi-stage execution plan, and run all steps to completion."""
        with self._lock:
            # Register steps from reference step types
            plan = self.control_plane.register_and_schedule(
                manifest=manifest,
                context=context,
                tenant_id=tenant_id,
                priority=priority,
            )

            results: dict[str, WorkflowStepResult] = {}
            current_context = context

            # Process all tasks from the scheduler queue
            while self.control_plane.scheduler.size() > 0:
                task = self.control_plane.scheduler.pop_next_task()
                if not task:
                    break

                res = self.worker.process_task(task, current_context)
                results[task.step_id] = res
                self.control_plane.scheduler.acknowledge_task(task.task_id)

                if not res.success and res.status != StepStatus.SKIPPED:
                    # Mark workflow failed
                    controller = self.control_plane.get_state_controller(context.workflow_id)
                    if controller and not controller.is_terminal():
                        controller.transition_to(WorkflowState.FAILED)
                    break

                if res.context_updates:
                    current_context = current_context.with_updates(runtime_updates={"temporary_state": res.context_updates})

            # Transition to COMPLETED if all steps succeeded
            controller = self.control_plane.get_state_controller(context.workflow_id)
            if controller and not controller.is_terminal():
                controller.transition_to(WorkflowState.COMPLETED)

            return results
