"""
Akaal — Risk Dependency Graph
==============================
Graph tracking relationships between detected risk items for Planner consumption.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RiskDependencyGraph:
    """Graph of inter-risk relationships."""
    parent_map: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    child_map: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    blocking_risks: List[str] = field(default_factory=list)

    def add_relationship(self, parent_risk_id: str, child_risk_id: str) -> None:
        self.parent_map[child_risk_id].append(parent_risk_id)
        self.child_map[parent_risk_id].append(child_risk_id)

    def add_blocking_risk(self, risk_id: str) -> None:
        if risk_id not in self.blocking_risks:
            self.blocking_risks.append(risk_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parent_map": dict(self.parent_map),
            "child_map": dict(self.child_map),
            "blocking_risks": self.blocking_risks,
        }
