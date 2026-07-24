"""RepairDependencyGraph: Topological ordering and circular dependency detection."""

from typing import Dict, List, Set


class RepairDependencyGraph:
    """Manages repair parent-child dependencies and computes topological execution order."""

    def __init__(self):
        # Node -> List of Dependent Nodes
        self._adj: Dict[str, List[str]] = {}
        self._in_degree: Dict[str, int] = {}

    def add_node(self, node: str) -> None:
        if node not in self._adj:
            self._adj[node] = []
            self._in_degree[node] = 0

    def add_dependency(self, parent: str, child: str) -> None:
        """Parent must be repaired BEFORE child."""
        self.add_node(parent)
        self.add_node(child)
        self._adj[parent].append(child)
        self._in_degree[child] += 1

    def detect_cycles(self) -> bool:
        """Check for circular repair dependencies."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def is_cyclic(curr: str) -> bool:
            visited.add(curr)
            rec_stack.add(curr)
            for child in self._adj.get(curr, []):
                if child not in visited:
                    if is_cyclic(child):
                        return True
                elif child in rec_stack:
                    return True
            rec_stack.remove(curr)
            return False

        for node in self._adj:
            if node not in visited:
                if is_cyclic(node):
                    return True
        return False

    def get_topological_order(self) -> List[str]:
        """Compute topological repair execution sequence."""
        if self.detect_cycles():
            raise ValueError("Circular dependency detected in repair graph.")

        in_deg = dict(self._in_degree)
        queue = [n for n, deg in in_deg.items() if deg == 0]
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for child in self._adj.get(node, []):
                in_deg[child] -= 1
                if in_deg[child] == 0:
                    queue.append(child)

        return order
