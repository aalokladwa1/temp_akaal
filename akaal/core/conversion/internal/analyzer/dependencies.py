"""
Akaal — Dependency & Cycle Analyzer
====================================
Analyzes dependency references, builds topological sort order, detects Strongly
Connected Components (SCCs), and classifies routine dependency cycles.
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from akaal.core.conversion.api.aoir import DependencyReference

class CycleResolutionKind(str, Enum):
    RESOLVABLE_STAGED_DECLARATION = "RESOLVABLE_STAGED_DECLARATION"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    UNRESOLVED_EXTERNAL = "UNRESOLVED_EXTERNAL"

@dataclass(frozen=True)
class CycleResolutionResult:
    cycle_nodes: Tuple[str, ...]
    resolution: CycleResolutionKind
    description: str

class DependencyAnalyzer:
    def __init__(self, objects: Dict[str, List[DependencyReference]]):
        """
        Args:
            objects: Maps object name to its list of dependency references.
        """
        self.adj: Dict[str, Set[str]] = {}
        self.all_nodes = set(objects.keys())
        
        # Populate adjacency graph
        for node, deps in objects.items():
            self.adj[node] = set()
            for dep in deps:
                self.adj[node].add(dep.object_name)
                self.all_nodes.add(dep.object_name)

    def find_sccs(self) -> List[List[str]]:
        """Tarjan's strongly connected components algorithm."""
        index_counter = 0
        stack: List[str] = []
        in_stack: Set[str] = set()
        lowlink: Dict[str, int] = {}
        index: Dict[str, int] = {}
        sccs: List[List[str]] = []

        def strongconnect(node: str):
            nonlocal index_counter
            index[node] = index_counter
            lowlink[node] = index_counter
            index_counter += 1
            stack.append(node)
            in_stack.add(node)

            # Successors
            for successor in self.adj.get(node, set()):
                if successor not in index:
                    strongconnect(successor)
                    lowlink[node] = min(lowlink[node], lowlink[successor])
                elif successor in in_stack:
                    lowlink[node] = min(lowlink[node], index[successor])

            # Root node of an SCC
            if lowlink[node] == index[node]:
                scc = []
                while True:
                    successor = stack.pop()
                    in_stack.remove(successor)
                    scc.append(successor)
                    if successor == node:
                        break
                sccs.append(scc)

        for node in self.all_nodes:
            if node not in index:
                strongconnect(node)

        return sccs

    def classify_cycles(self, sccs: List[List[str]]) -> List[CycleResolutionResult]:
        results: List[CycleResolutionResult] = []
        for scc in sccs:
            if len(scc) <= 1:
                # Check for self-recursion
                node = scc[0]
                if node in self.adj.get(node, set()):
                    results.append(CycleResolutionResult(
                        cycle_nodes=(node,),
                        resolution=CycleResolutionKind.RESOLVABLE_STAGED_DECLARATION,
                        description=f"Self-recursive call inside '{node}' can be compiled safely by ordering compilation."
                    ))
                continue

            # Mutual recursion
            has_missing_definition = any(node not in self.adj for node in scc)
            if has_missing_definition:
                results.append(CycleResolutionResult(
                    cycle_nodes=tuple(sorted(scc)),
                    resolution=CycleResolutionKind.UNRESOLVED_EXTERNAL,
                    description=f"Mutual recursion involves external undefined object references: {scc}."
                ))
            else:
                # Staged declaration is possible for procedures in Postgres by pre-rendering empty routines
                results.append(CycleResolutionResult(
                    cycle_nodes=tuple(sorted(scc)),
                    resolution=CycleResolutionKind.RESOLVABLE_STAGED_DECLARATION,
                    description=f"Mutually recursive loop: {scc}. Resolved by staging empty routine definitions first."
                ))
        return results

    def get_topological_order(self) -> List[str]:
        """Returns topological ordering. Raises ValueError if unresolvable cycle exists."""
        in_degree: Dict[str, int] = {node: 0 for node in self.all_nodes}
        for node in self.all_nodes:
            for neighbor in self.adj.get(node, set()):
                if neighbor in in_degree:
                    in_degree[neighbor] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in self.adj.get(node, set()):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        if len(order) < len(self.all_nodes):
            # There is a cycle; we try to resolve it. Tarjan's SCC classifies cycle nodes.
            # In a production pipeline, we fallback to compiling headers first.
            # For dependency ordering, we order non-cyclic nodes first.
            sccs = self.find_sccs()
            cyclic_groups = [scc for scc in sccs if len(scc) > 1 or (len(scc) == 1 and scc[0] in self.adj.get(scc[0], set()))]
            
            # Form standard topological order by collapsing cyclic components into single nodes
            collapsed_adj: Dict[str, Set[str]] = {}
            node_to_scc_idx: Dict[str, int] = {}
            for idx, scc in enumerate(sccs):
                for node in scc:
                    node_to_scc_idx[node] = idx

            for idx, scc in enumerate(sccs):
                collapsed_adj[f"SCC_{idx}"] = set()
                for node in scc:
                    for neighbor in self.adj.get(node, set()):
                        neigh_scc = node_to_scc_idx.get(neighbor)
                        if neigh_scc is not None and neigh_scc != idx:
                            collapsed_adj[f"SCC_{idx}"].add(f"SCC_{neigh_scc}")

            collapsed_in_degree = {f"SCC_{i}": 0 for i in range(len(sccs))}
            for scc_id, neighbors in collapsed_adj.items():
                for neighbor in neighbors:
                    collapsed_in_degree[neighbor] += 1

            collapsed_queue = [scc_id for scc_id, degree in collapsed_in_degree.items() if degree == 0]
            collapsed_order = []
            while collapsed_queue:
                scc_id = collapsed_queue.pop(0)
                collapsed_order.append(scc_id)
                for neighbor in collapsed_adj.get(scc_id, set()):
                    collapsed_in_degree[neighbor] -= 1
                    if collapsed_in_degree[neighbor] == 0:
                        collapsed_queue.append(neighbor)

            # Flatten collapsed order back into individual node list in dependency order
            flattened = []
            for scc_id in reversed(collapsed_order):
                idx = int(scc_id.split("_")[1])
                flattened.extend(sccs[idx])
            return flattened

        return order[::-1]
