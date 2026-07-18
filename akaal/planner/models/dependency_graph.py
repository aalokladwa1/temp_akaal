"""
Akaal — Planner Dependency Graph
================================
Planner-specific dependency graph tracking critical chains and blocking operations.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PlannerDependencyGraph:
    critical_chain: List[str] = field(default_factory=list)
    blocking_operations: List[str] = field(default_factory=list)
    independent_groups: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "critical_chain": self.critical_chain,
            "blocking_operations": self.blocking_operations,
            "independent_groups": self.independent_groups,
        }
