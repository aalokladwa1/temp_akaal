"""
tests.unit.engine_schema.test_dependency_cycle_breaking
=======================================================
Unit tests for multi-domain DAG construction and circular FK cycle breaking (SCH-061, SCH-062).
"""

import pytest

from akaalEngine.schema.dependency.cycle_breaker import CycleBreaker
from akaalEngine.schema.dependency.graph import DependencyNode, MultiDomainDependencyGraph
from akaalEngine.schema.dependency.sorter import TopologicalSorter


def test_circular_foreign_key_cycle_breaking():
    # Table A has FK referencing Table B, and Table B has FK referencing Table A
    graph = MultiDomainDependencyGraph()

    graph.add_node(DependencyNode(node_id="table:public.author", object_type="TABLE", schema_name="public", object_name="author"))
    graph.add_node(DependencyNode(node_id="table:public.book", object_type="TABLE", schema_name="public", object_name="book"))

    # Author's favorite book -> Book
    graph.add_edge("table:public.author", "table:public.book", dep_type="FOREIGN_KEY")
    # Book's primary author -> Author
    graph.add_edge("table:public.book", "table:public.author", dep_type="FOREIGN_KEY")

    # Initial graph has cycle
    sccs = TopologicalSorter.detect_scc(graph)
    assert len(sccs) == 1
    assert set(sccs[0]) == {"table:public.author", "table:public.book"}

    # Apply CycleBreaker
    pruned = CycleBreaker.break_fk_cycles(graph)
    sccs_pruned = TopologicalSorter.detect_scc(pruned)
    assert len(sccs_pruned) == 0  # Cycle successfully broken

    ordered = TopologicalSorter.sort(pruned)
    assert len(ordered) == 2
    assert set(ordered) == {"table:public.author", "table:public.book"}
