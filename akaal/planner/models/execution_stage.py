"""
Akaal — Execution Stage Model
=============================
Dataclass representing an execution stage containing grouped tasks and stage policies.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
from akaal.planner.models.execution_task import ExecutionTask
from akaal.planner.models.stage_policy import StagePolicy


@dataclass
class ExecutionStage:
    stage_id: str
    stage_name: str
    stage_order: int
    tasks: List[ExecutionTask] = field(default_factory=list)
    policy: StagePolicy = field(default_factory=StagePolicy)
    stage_dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "stage_order": self.stage_order,
            "tasks": [t.to_dict() for t in self.tasks],
            "policy": self.policy.to_dict(),
            "stage_dependencies": self.stage_dependencies,
        }
