"""Data Plane Worker managing activity execution, step pipeline, and heartbeat."""

import threading
from typing import Optional
from akaal.workflow.execution.pipeline import ExecutionPipeline
from akaal.workflow.models.context import WorkflowContext
from akaal.workflow.models.results import StepStatus, WorkflowStepResult
from akaal.workflow.queues.interfaces import StepExecutionTask
from akaal.workflow.registry.registry import WorkflowStepRegistry


class DataPlaneWorker:
    """Data Plane worker node executing step payloads assigned by the control plane."""

    def __init__(self, worker_id: str, registry: WorkflowStepRegistry) -> None:
        self.worker_id = worker_id
        self.registry = registry
        self.pipeline = ExecutionPipeline()
        self._active_count: int = 0
        self._lock = threading.Lock()

    def process_task(self, task: StepExecutionTask, context: WorkflowContext) -> WorkflowStepResult:
        """Execute a step activity payload."""
        with self._lock:
            self._active_count += 1
        try:
            step_instance = self.registry.resolve(task.step_type, task.step_id)
            result, _ = self.pipeline.run_pipeline(step_instance, context)
            return result
        finally:
            with self._lock:
                self._active_count -= 1

    @property
    def active_count(self) -> int:
        with self._lock:
            return self._active_count
