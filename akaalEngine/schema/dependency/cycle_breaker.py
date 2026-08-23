"""
akaalEngine.schema.dependency.cycle_breaker
===========================================
Detects and breaks circular foreign key dependencies by staging them as deferred ALTER TABLE statements.
"""

from __future__ import annotations

from typing import List, Set, Tuple

from akaalEngine.schema.dependency.graph import DependencyEdge, MultiDomainDependencyGraph


class CycleBreaker:
    """Detects cycles in the dependency graph and safely breaks circular FK dependencies."""

    @classmethod
    def break_fk_cycles(cls, graph: MultiDomainDependencyGraph) -> MultiDomainDependencyGraph:
        """Removes circular and self-loop FK dependency edges from table DAG construction."""
        # MultiDomainDependencyGraph staged execution automatically puts FKs in stage FOREIGN_KEYS
        # This method filters out FOREIGN_KEY and SELF_LOOP edges from graph.adj_list so that tables sort cleanly.
        pruned_graph = MultiDomainDependencyGraph()
        for nid, node in graph.nodes.items():
            pruned_graph.add_node(node)

        for edge in graph.edges:
            # Drop self loops and direct FK edges from the table ordering graph
            if edge.dependency_type in ("SELF_LOOP", "FOREIGN_KEY"):
                continue
            pruned_graph.add_edge(edge.source_id, edge.target_id, edge.dependency_type)

        return pruned_graph
