"""
AKAAL Platform 6 — Governance Dependency Graph.
"""

from typing import Dict, List, Set, Optional
from akaal.governance.domain.models import GovernanceDependencyNode
from akaal.governance.domain.exceptions import CircularDependencyError


class GovernanceDependencyGraph:
    """DAG modeling dependencies across policies, rules, workflows, waivers, and SoD constraints."""

    def __init__(self) -> None:
        self._nodes: Dict[str, GovernanceDependencyNode] = {}

    def add_node(self, node: GovernanceDependencyNode) -> None:
        self._nodes[node.artifact_id] = node

    def get_node(self, artifact_id: str) -> Optional[GovernanceDependencyNode]:
        return self._nodes.get(artifact_id)

    def detect_circular_dependencies(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(curr_id: str) -> bool:
            visited.add(curr_id)
            rec_stack.add(curr_id)

            node = self._nodes.get(curr_id)
            if node:
                for dep in node.dependencies:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(curr_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False
