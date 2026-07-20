"""Saga Manager orchestrating Saga compensation execution upon workflow failure."""

import threading
from typing import List
from akaal.workflow.saga.stack import CompensationStack, CompensationStep


class SagaManager:
    """Orchestrates Saga compensation execution by popping LIFO stack entries."""

    def __init__(self) -> None:
        self._stacks: dict[str, CompensationStack] = {}
        self._lock = threading.Lock()

    def get_or_create_stack(self, workflow_id: str) -> CompensationStack:
        with self._lock:
            if workflow_id not in self._stacks:
                self._stacks[workflow_id] = CompensationStack()
            return self._stacks[workflow_id]

    def register_compensation(self, workflow_id: str, step_id: str, compensation_action: str, parameters: dict) -> None:
        stack = self.get_or_create_stack(workflow_id)
        step = CompensationStep(step_id=step_id, compensation_action=compensation_action, parameters=parameters)
        stack.push(step)

    def execute_compensation(self, workflow_id: str) -> List[CompensationStep]:
        """Pop and execute all registered compensation steps in LIFO order."""
        stack = self.get_or_create_stack(workflow_id)
        executed: List[CompensationStep] = []
        while not stack.is_empty():
            step = stack.pop()
            if step:
                executed.append(step)
        return executed
