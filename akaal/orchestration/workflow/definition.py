"""
WorkflowDefinition abstraction.
Encapsulates workflow name, version, step sequence, execution policies, and approval rules.
The WorkflowEngine executes WorkflowDefinition instances without hardcoding business phases.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from akaal.orchestration.workflow.step import WorkflowStep


@dataclass
class WorkflowDefinition:
    """
    WorkflowDefinition blueprint executed by the WorkflowEngine.
    """
    name: str
    version: str
    steps: List[WorkflowStep]
    policies: Dict[str, Any] = field(default_factory=dict)
    approval_rules: Dict[str, Any] = field(default_factory=dict)

    def get_step_names(self) -> List[str]:
        return [s.name for s in self.steps]

    def get_step(self, name: str) -> WorkflowStep:
        for step in self.steps:
            if step.name == name:
                return step
        raise KeyError(f"Step '{name}' not found in WorkflowDefinition '{self.name}'.")
