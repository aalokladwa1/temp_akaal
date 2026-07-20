"""WorkflowClient Public Facade for AKAAL Platform Consumers."""

from typing import Any, Mapping, Tuple
from akaal.workflow.contracts.validator import ManifestValidator
from akaal.workflow.engine.engine import WorkflowEngine
from akaal.workflow.execution_records.records import WorkflowExecutionTrace
from akaal.workflow.interfaces.base import IStep
from akaal.workflow.models.metadata import StepDefinition, WorkflowManifest, WorkflowMetadata
from akaal.workflow.registry.registry import WorkflowStepRegistry


class WorkflowClient:
    """Public Client Facade providing simple API access to the Workflow Platform."""

    def __init__(self, engine: WorkflowEngine | None = None, registry: WorkflowStepRegistry | None = None) -> None:
        self._registry = registry or (engine._registry if engine else WorkflowStepRegistry())
        self._engine = engine or WorkflowEngine(registry=self._registry)

    @property
    def registry(self) -> WorkflowStepRegistry:
        return self._registry

    @property
    def engine(self) -> WorkflowEngine:
        return self._engine

    def register_step(self, step_type: str, step_class: type[IStep]) -> None:
        """Register a step class with the step registry."""
        self._registry.register(step_type, step_class)

    def submit_workflow(self, manifest: WorkflowManifest) -> None:
        """Validate structural manifest integrity and register with the workflow engine."""
        ManifestValidator.validate_or_raise(manifest)
        self._engine.register_manifest(manifest)

    def execute_workflow(self, workflow_id: str, parameters: dict[str, Any] | None = None) -> WorkflowExecutionTrace:
        """Execute a submitted workflow by ID."""
        return self._engine.execute(workflow_id, parameters=parameters)

    def pause_workflow(self, workflow_id: str) -> None:
        """Pause a running workflow."""
        self._engine.pause(workflow_id)

    def resume_workflow(self, workflow_id: str) -> WorkflowExecutionTrace:
        """Resume a paused workflow."""
        return self._engine.resume(workflow_id)

    def cancel_workflow(self, workflow_id: str) -> None:
        """Cancel a running or paused workflow."""
        self._engine.cancel(workflow_id)

    def rollback_workflow(self, workflow_id: str) -> WorkflowExecutionTrace:
        """Trigger compensating rollback for a workflow."""
        return self._engine.rollback(workflow_id)
