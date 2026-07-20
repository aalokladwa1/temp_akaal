"""Workflow Step Registry with Encapsulated Private Step Factory."""

from typing import Dict, Tuple, Type
from akaal.workflow.exceptions import StepNotFoundException
from akaal.workflow.interfaces.base import IStep


class _StepFactory:
    """Private step instantiation factory encapsulated strictly inside WorkflowStepRegistry."""

    @staticmethod
    def create_step(step_class: Type[IStep], step_id: str, **kwargs) -> IStep:
        """Instantiate step class with step_id and optional keyword arguments."""
        try:
            return step_class(step_id=step_id, **kwargs)
        except TypeError:
            # Fallback if step constructor does not take kwargs or step_id in init
            step_obj = step_class(**kwargs)
            if hasattr(step_obj, "_step_id"):
                setattr(step_obj, "_step_id", step_id)
            return step_obj


class WorkflowStepRegistry:
    """Registry managing workflow step registration and resolution.
    
    WorkflowEngine interacts ONLY with this registry. Instantiation mechanics via _StepFactory
    are strictly private internal implementation details.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Type[IStep]] = {}

    def register(self, step_type: str, step_class: Type[IStep]) -> None:
        """Register a step type with its concrete step implementation class."""
        self._registry[step_type] = step_class

    def unregister(self, step_type: str) -> None:
        """Unregister a step type from the registry."""
        self._registry.pop(step_type, None)

    def resolve(self, step_type: str, step_id: str, **kwargs) -> IStep:
        """Resolve and instantiate a registered step type using the internal StepFactory."""
        step_class = self._registry.get(step_type)
        if not step_class:
            raise StepNotFoundException(step_type)
        return _StepFactory.create_step(step_class, step_id=step_id, **kwargs)

    def list_registered_steps(self) -> Tuple[str, ...]:
        """Return tuple of registered step types."""
        return tuple(sorted(self._registry.keys()))

    def clear(self) -> None:
        """Clear all registered step types."""
        self._registry.clear()
