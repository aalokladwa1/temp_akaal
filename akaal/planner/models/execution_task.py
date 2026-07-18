"""
Akaal — Execution Task Model
============================
Immutable dataclass representing an individual task node within ExecutionGraph.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from akaal.planner.models.execution_state import ExecutionState
from akaal.planner.models.dependency_semantics import DependencySemantics


@dataclass(frozen=True)
class ExecutionTask:
    task_id: str
    task_name: str
    task_type: str  # "SCHEMA_DDL", "DATA_BULK", "VALIDATION_CHECK", "CHECKPOINT_GATE", "ROLLBACK_ACTION"
    target_object_id: str
    state: ExecutionState = ExecutionState.PLANNED
    dependencies: List[str] = field(default_factory=list)  # dependent task_ids
    dependency_semantics: Dict[str, str] = field(default_factory=dict)  # task_id -> DependencySemantics
    estimated_duration_seconds: float = 60.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    parallel_group_id: Optional[str] = None
    stage_id: str = "stage_1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "task_type": self.task_type,
            "target_object_id": self.target_object_id,
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "dependencies": self.dependencies,
            "dependency_semantics": self.dependency_semantics,
            "estimated_duration_seconds": round(self.estimated_duration_seconds, 2),
            "parameters": self.parameters,
            "parallel_group_id": self.parallel_group_id,
            "stage_id": self.stage_id,
        }
