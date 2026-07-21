"""
AKAAL Platform 5 — Tarjan Topological Sorter

Provides topological sorting with cycle detection and automatic rollback order generation.
"""

from typing import Dict, List, Set

from akaal.schema.domain.errors import ValidationError
from akaal.schema.graph.node import SchemaNode


class TarjanTopologicalSorter:
    """Topological sorter using Tarjan's algorithm to compute execution order."""

    @staticmethod
    def sort(nodes: Dict[str, SchemaNode]) -> List[SchemaNode]:
        visited: Set[str] = set()
        visiting: Set[str] = set()
        order: List[SchemaNode] = []

        def dfs(node_id: str) -> None:
            if node_id in visiting:
                raise ValidationError(
                    message=f"Circular dependency cycle detected at schema node '{node_id}'.",
                    recovery_recommendation="Break cycle by splitting FK constraints or deferring constraint creation."
                )
            if node_id not in visited:
                visiting.add(node_id)
                node = nodes[node_id]
                for dep in node.dependencies:
                    if dep in nodes:
                        dfs(dep)
                visiting.remove(node_id)
                visited.add(node_id)
                order.append(node)

        for nid in list(nodes.keys()):
            if nid not in visited:
                dfs(nid)

        return order
