"""
WorkflowDefinition abstraction.
Encapsulates workflow name, version, immutable step sequence tuple, execution policies, and approval rules.
The WorkflowEngine executes WorkflowDefinition instances without hardcoding business phases.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Sequence

from akaal.orchestration.workflow.step import WorkflowStep


@dataclass(frozen=True)
class WorkflowDefinition:
    """
    Immutable WorkflowDefinition blueprint executed by the WorkflowEngine.
    Step sequence is stored as an immutable tuple to preserve deterministic execution order.
    """
    name: str
    version: str
    steps: Tuple[WorkflowStep, ...] = field(default_factory=tuple)
    policies: Dict[str, Any] = field(default_factory=dict)
    approval_rules: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.steps, tuple):
            object.__setattr__(self, "steps", tuple(self.steps))

    def get_step_names(self) -> List[str]:
        return [s.name for s in self.steps]

    def get_step(self, name: str) -> WorkflowStep:
        for step in self.steps:
            if step.name == name:
                return step
        raise KeyError(f"Step '{name}' not found in WorkflowDefinition '{self.name}'.")
