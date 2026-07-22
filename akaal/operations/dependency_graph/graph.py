"""
Enterprise Dependency Graph.
Tracks dependencies across platforms, workers, resources, and infrastructure for impact analysis.
"""

from typing import Dict, List, Set, Any
from threading import RLock


class DependencyGraph:
    """Directed dependency graph for blast radius analysis."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._dependencies: Dict[str, Set[str]] = {}  # node -> set of nodes it depends on
        self._dependents: Dict[str, Set[str]] = {}    # node -> set of nodes that depend on it

    def add_dependency(self, target: str, depends_on: str) -> None:
        """Target node depends on depends_on node."""
        with self._lock:
            if target not in self._dependencies:
                self._dependencies[target] = set()
            self._dependencies[target].add(depends_on)

            if depends_on not in self._dependents:
                self._dependents[depends_on] = set()
            self._dependents[depends_on].add(target)

    def analyze_impact(self, failed_node: str) -> Dict[str, Any]:
        """Calculates downstream nodes impacted if failed_node goes down."""
        with self._lock:
            visited = set()
            queue = [failed_node]

            while queue:
                current = queue.pop(0)
                if current not in visited:
                    visited.add(current)
                    queue.extend(self._dependents.get(current, set()) - visited)

            visited.discard(failed_node)  # Remove self
            return {
                "failed_node": failed_node,
                "impacted_nodes": list(visited),
                "impact_count": len(visited)
            }
