"""
Workflow Step Interface for Enterprise Orchestration Platform.
Every workflow step implements this standardized lifecycle contract.
Future business workflow steps can be introduced without modifying the Workflow Engine.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from akaal.orchestration.workflow.context import WorkflowContext


class WorkflowStep(ABC):
    """
    Abstract base class for all workflow steps.
    Mandates implementation of full execution lifecycle.
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def initialize(self, context: WorkflowContext) -> None:
        """Initialize step resources and state."""
        pass

    @abstractmethod
    def validate(self, context: WorkflowContext) -> bool:
        """Validate step preconditions and input requirements."""
        pass

    @abstractmethod
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute step logic. Must be deterministic."""
        pass

    @abstractmethod
    def checkpoint(self, context: WorkflowContext) -> Dict[str, Any]:
        """Capture step checkpoint state snapshot."""
        pass

    @abstractmethod
    def resume(self, context: WorkflowContext, checkpoint_data: Dict[str, Any]) -> None:
        """Resume step execution from checkpoint state."""
        pass

    @abstractmethod
    def rollback(self, context: WorkflowContext) -> None:
        """Rollback step modifications on failure or cancellation."""
        pass

    @abstractmethod
    def cleanup(self, context: WorkflowContext) -> None:
        """Cleanup step resources."""
        pass
