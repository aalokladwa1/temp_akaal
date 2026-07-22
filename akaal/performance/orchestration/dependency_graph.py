"""
Optimization Dependency Graph.
Guarantees deterministic, prioritized optimizer execution.
"""

from typing import List, Dict, Set, Optional
from threading import RLock

from akaal.performance.failures.classification import PerformanceEngineError, PerformanceFailureType


class OptimizationDependencyGraph:
    """Directed Acyclic Graph (DAG) for sorting optimizer plugins topologically."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._dependencies: Dict[str, Set[str]] = {}
        self._default_order: List[str] = [
            "discovery",
            "governor",
            "batch",
            "parallel",
            "compression",
            "load_balancer",
            "validation"
        ]
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        # Build topological links for default items
        for idx in range(len(self._default_order)):
            node = self._default_order[idx]
            self._dependencies[node] = set()
            for prev_idx in range(idx):
                self._dependencies[node].add(self._default_order[prev_idx])

    def register_plugin(self, plugin_name: str, depends_on: Optional[List[str]] = None) -> None:
        with self._lock:
            p_name = plugin_name.lower()
            if p_name not in self._dependencies:
                self._dependencies[p_name] = set()
            if depends_on:
                for dep in depends_on:
                    self._dependencies[p_name].add(dep.lower())

    def sort_execution_order(self) -> List[str]:
        """Performs a topological sort on registered dependencies, detecting circular loops."""
        with self._lock:
            visited: Set[str] = set()
            temp_mark: Set[str] = set()
            order: List[str] = []

            def visit(node: str) -> None:
                if node in temp_mark:
                    raise PerformanceEngineError(
                        PerformanceFailureType.RULE_CONFLICT,
                        f"Circular dependency detected in optimizer dependency graph at node '{node}'."
                    )
                if node not in visited:
                    temp_mark.add(node)
                    # Visit dependencies first
                    for dep in self._dependencies.get(node, []):
                        if dep in self._dependencies:  # ignore unregistered deps
                            visit(dep)
                    temp_mark.remove(node)
                    visited.add(node)
                    order.append(node)

            for node in self._dependencies:
                if node not in visited:
                    visit(node)

            return order
