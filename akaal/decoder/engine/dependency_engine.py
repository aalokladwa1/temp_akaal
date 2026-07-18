"""
Akaal — Dependency Engine
=========================
Single-responsibility engine building DAG dependency ordering for CanonicalObjectGraph.
"""

from typing import List, Dict, Any, Tuple
from akaal.decoder.models.canonical_graph import CanonicalObjectGraph
from akaal.decoder.models.canonical_object import CanonicalObject


class DependencyEngine:
    """Builds DAG relationship graphs across canonical objects."""

    def resolve_dependencies(self, graph: CanonicalObjectGraph) -> Tuple[List[CanonicalObject], Dict[str, Any]]:
        ordered = graph.topological_sort()
        summary = {
            "total_nodes": len(graph.get_all_objects()),
            "ordered_canonical_ids": [obj.identity.canonical_id for obj in ordered],
        }
        return ordered, summary
