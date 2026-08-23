"""
tests.unit.engine_schema.test_tarjan_topological_sort
=====================================================
Unit tests for Tarjan SCC cycle detection and deterministic topological sorting (SCH-063).
"""

import pytest

from akaalEngine.schema.dependency.graph import DependencyNode, MultiDomainDependencyGraph
from akaalEngine.schema.dependency.sorter import TopologicalSorter


def test_deterministic_topological_sort():
    # Diamond graph: A depends on B and C; B depends on D; C depends on D.
    graph = MultiDomainDependencyGraph()
    for name in ["A", "B", "C", "D"]:
        graph.add_node(DependencyNode(node_id=name, object_type="TABLE", schema_name="public", object_name=name))

    graph.add_edge("A", "B")
    graph.add_edge("A", "C")
    graph.add_edge("B", "D")
    graph.add_edge("C", "D")

    # Topological order should place prerequisites before dependents: D must come before B and C, which come before A.
    order1 = TopologicalSorter.sort(graph)
    order2 = TopologicalSorter.sort(graph)

    assert order1 == order2  # Determinism
    assert order1.index("D") < order1.index("B")
    assert order1.index("D") < order1.index("C")
    assert order1.index("B") < order1.index("A")
    assert order1.index("C") < order1.index("A")


def test_tarjan_scc_cycle_detection():
    # 3-node cycle: X -> Y -> Z -> X
    graph = MultiDomainDependencyGraph()
    for name in ["X", "Y", "Z", "W"]:
        graph.add_node(DependencyNode(node_id=name, object_type="TABLE", schema_name="public", object_name=name))

    graph.add_edge("X", "Y")
    graph.add_edge("Y", "Z")
    graph.add_edge("Z", "X")
    graph.add_edge("W", "X")

    sccs = TopologicalSorter.detect_scc(graph)
    assert len(sccs) == 1
    assert set(sccs[0]) == {"X", "Y", "Z"}
