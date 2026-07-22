"""
Operational Workflow Engine.
Executes reusable operational runbooks and procedure steps with validation and rollback.
"""

from typing import Dict, List, Callable, Any, Optional
from threading import RLock
import time


class OperationalStep:
    def __init__(self, step_name: str, handler: Callable[[], bool], rollback_handler: Optional[Callable[[], None]] = None) -> None:
        self.step_name = step_name
        self.handler = handler
        self.rollback_handler = rollback_handler


class OperationalWorkflow:
    def __init__(self, workflow_name: str, steps: List[OperationalStep]) -> None:
        self.workflow_name = workflow_name
        self.steps = steps
        self.executed_steps: List[str] = []


class OperationalWorkflowEngine:
    """Executes operational runbook steps with rollback capabilities."""

    def __init__(self) -> None:
        self._lock = RLock()

    def execute_workflow(self, workflow: OperationalWorkflow) -> Dict[str, Any]:
        with self._lock:
            completed = []
            for step in workflow.steps:
                try:
                    success = step.handler()
                    if not success:
                        # Step failed, rollback executed steps in reverse
                        self._rollback(workflow, completed)
                        return {
                            "workflow": workflow.workflow_name,
                            "status": "FAILED",
                            "failed_step": step.step_name,
                            "executed_steps": completed
                        }
                    completed.append(step.step_name)
                except Exception as e:
                    self._rollback(workflow, completed)
                    return {
                        "workflow": workflow.workflow_name,
                        "status": "FAILED",
                        "error": str(e),
                        "failed_step": step.step_name,
                        "executed_steps": completed
                    }

            return {
                "workflow": workflow.workflow_name,
                "status": "COMPLETED",
                "executed_steps": completed
            }

    def _rollback(self, workflow: OperationalWorkflow, completed_step_names: List[str]) -> None:
        name_map = {step.step_name: step for step in workflow.steps}
        for sname in reversed(completed_step_names):
            step = name_map.get(sname)
            if step and step.rollback_handler:
                try:
                    step.rollback_handler()
                except Exception:
                    pass
