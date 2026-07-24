"""
AKAAL Platform 6 — Governance Dependency Resolver.
"""

from typing import List, Set
from akaal.governance.dependencies.graph import GovernanceDependencyGraph


class GovernanceDependencyResolver:
    """Resolves complete transitive resolution chains for governance artifacts."""

    def resolve_transitive_dependencies(self, graph: GovernanceDependencyGraph, start_artifact_id: str) -> List[str]:
        resolved: List[str] = []
        visited: Set[str] = set()

        def dfs(curr_id: str):
            visited.add(curr_id)
            node = graph.get_node(curr_id)
            if node:
                for dep in node.dependencies:
                    if dep not in visited:
                        dfs(dep)
            resolved.append(curr_id)

        dfs(start_artifact_id)
        return resolved
