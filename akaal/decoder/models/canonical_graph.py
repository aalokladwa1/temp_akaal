"""
Akaal — Canonical Object Graph
==============================
Unified Object Graph connecting all normalized CanonicalObject instances.
"""

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Any
from akaal.decoder.models.canonical_object import CanonicalObject


class CanonicalObjectGraph:
    """Unified Graph storing all normalized CanonicalObjects and inter-object relationships."""

    def __init__(self) -> None:
        self._nodes: Dict[str, CanonicalObject] = {}
        self._edges: Dict[str, List[str]] = defaultdict(list)
        self._reverse_edges: Dict[str, List[str]] = defaultdict(list)

    def add_object(self, obj: CanonicalObject) -> None:
        c_id = obj.identity.canonical_id
        self._nodes[c_id] = obj

        for ref_id in obj.references:
            self.add_edge(c_id, ref_id)

    def add_edge(self, source_id: str, target_id: str) -> None:
        self._edges[source_id].append(target_id)
        self._reverse_edges[target_id].append(source_id)

    def get_object(self, canonical_id: str) -> Optional[CanonicalObject]:
        return self._nodes.get(canonical_id)

    def get_all_objects(self) -> List[CanonicalObject]:
        return list(self._nodes.values())

    def topological_sort(self) -> List[CanonicalObject]:
        in_degree = {c_id: 0 for c_id in self._nodes}
        for src, targets in self._edges.items():
            for t in targets:
                if t in in_degree:
                    in_degree[t] += 1

        queue = deque([c_id for c_id, deg in in_degree.items() if deg == 0])
        sorted_nodes: List[CanonicalObject] = []

        while queue:
            curr = queue.popleft()
            if curr in self._nodes:
                sorted_nodes.append(self._nodes[curr])
            for neighbor in self._edges.get(curr, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        if len(sorted_nodes) != len(self._nodes):
            # Fallback if cycle present
            return list(self._nodes.values())

        return sorted_nodes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_objects": len(self._nodes),
            "nodes": [obj.to_dict() for obj in self._nodes.values()],
            "edges": dict(self._edges),
        }
