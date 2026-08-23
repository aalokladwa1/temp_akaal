"""
akaalEngine.schema.dependency.sorter
====================================
Deterministic topological sorting and Strongly Connected Component (SCC) cycle detection.
Implements Kahn's algorithm with alphabetical tie-breaking and Tarjan's SCC algorithm.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Set, Tuple

from akaalEngine.schema.dependency.graph import MultiDomainDependencyGraph


class TopologicalSorter:
    """Performs deterministic topological sorting and cycle detection on schema dependency graphs."""

    @classmethod
    def sort(cls, graph: MultiDomainDependencyGraph) -> List[str]:
        """Topologically orders graph nodes using Kahn's algorithm with min-heap for deterministic tie-breaking."""
        # Calculate in-degree: number of prerequisites a node depends on
        in_degree: Dict[str, int] = {nid: 0 for nid in graph.nodes}
        for nid, prereqs in graph.adj_list.items():
            valid_prereqs = [p for p in prereqs if p in graph.nodes]
            in_degree[nid] = len(valid_prereqs)

        # Min-heap priority queue for deterministic ordering
        pq: List[str] = [nid for nid, deg in in_degree.items() if deg == 0]
        heapq.heapify(pq)

        ordered: List[str] = []
        while pq:
            curr = heapq.heappop(pq)
            ordered.append(curr)

            # For each dependent node that depends on curr
            for dep in graph.reverse_adj.get(curr, ()):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        heapq.heappush(pq, dep)

        # If some nodes were not ordered due to unresolvable cycles, append remaining sorted deterministically
        if len(ordered) < len(graph.nodes):
            remaining = sorted([nid for nid in graph.nodes if nid not in set(ordered)])
            ordered.extend(remaining)

        return ordered

    @classmethod
    def detect_scc(cls, graph: MultiDomainDependencyGraph) -> List[List[str]]:
        """Tarjan's algorithm for finding Strongly Connected Components (cycles)."""
        index = 0
        stack: List[str] = []
        on_stack: Set[str] = set()
        indices: Dict[str, int] = {}
        lowlinks: Dict[str, int] = {}
        sccs: List[List[str]] = []

        def strongconnect(node: str) -> None:
            nonlocal index
            indices[node] = index
            lowlinks[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for neighbor in graph.adj_list.get(node, ()):
                if neighbor not in graph.nodes:
                    continue
                if neighbor not in indices:
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif neighbor in on_stack:
                    lowlinks[node] = min(lowlinks[node], indices[neighbor])

            if lowlinks[node] == indices[node]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == node:
                        break
                if len(scc) > 1:
                    sccs.append(sorted(scc))

        for nid in sorted(graph.nodes.keys()):
            if nid not in indices:
                strongconnect(nid)

        return sccs
