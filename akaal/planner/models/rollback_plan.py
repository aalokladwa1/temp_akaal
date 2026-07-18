"""
Akaal — Rollback Plan & Rollback Graph Model
=============================================
Expanded RollbackGraph representation with dependencies, compensation chains, recovery nodes,
and rollback ordering. Planner plans rollback operations but never executes them.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RollbackNode:
    rollback_id: str
    task_id: str
    compensation_action: str
    depends_on: List[str] = field(default_factory=list)
    recovery_point_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "task_id": self.task_id,
            "compensation_action": self.compensation_action,
            "depends_on": self.depends_on,
            "recovery_point_id": self.recovery_point_id,
        }


@dataclass
class RollbackGraph:
    nodes: Dict[str, RollbackNode] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    ordered_rollback_ids: List[str] = field(default_factory=list)

    def add_node(self, node: RollbackNode) -> None:
        self.nodes[node.rollback_id] = node
        for dep in node.depends_on:
            self.edges[dep].append(node.rollback_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": dict(self.edges),
            "ordered_rollback_ids": self.ordered_rollback_ids,
        }


@dataclass
class RollbackPlan:
    strategy: str = "FULL_COMPENSATION"
    rollback_graph: RollbackGraph = field(default_factory=RollbackGraph)
    recovery_points: List[str] = field(default_factory=list)
    rollback_validation_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "rollback_graph": self.rollback_graph.to_dict(),
            "recovery_points": self.recovery_points,
            "rollback_validation_required": self.rollback_validation_required,
        }
