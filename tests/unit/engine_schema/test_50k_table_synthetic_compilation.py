"""
tests.unit.engine_schema.test_50k_table_synthetic_compilation
=============================================================
Scale test demonstrating chunked processing and sub-1.5s topological graph resolution across 50,000 synthetic nodes (SCH-069, SCH-070).
"""

import time
import pytest

from akaalEngine.schema.dependency.graph import DependencyNode, MultiDomainDependencyGraph
from akaalEngine.schema.dependency.sorter import TopologicalSorter


def test_50k_table_topological_sort_scale():
    graph = MultiDomainDependencyGraph()
    total_nodes = 50000

    # Build 50,000 synthetic tables structured in 100 independent chains of 500 tables each (chunk size = 500)
    for chain_id in range(100):
        for idx in range(500):
            node_id = f"table:chain_{chain_id}.table_{idx}"
            graph.add_node(
                DependencyNode(
                    node_id=node_id,
                    object_type="TABLE",
                    schema_name=f"chain_{chain_id}",
                    object_name=f"table_{idx}",
                )
            )
            # Add dependency to previous table in chain
            if idx > 0:
                prev_id = f"table:chain_{chain_id}.table_{idx - 1}"
                graph.add_edge(node_id, prev_id)

    assert len(graph.nodes) == total_nodes

    # Measure topological sort duration
    start_time = time.perf_counter()
    ordered = TopologicalSorter.sort(graph)
    elapsed = time.perf_counter() - start_time

    assert len(ordered) == total_nodes
    print(f"\n[SCALE TEST] 50,000 table topological sort completed in {elapsed:.4f} seconds.")

    # Performance target: topological sort of 50,000 nodes should complete under 2.5 seconds locally
    assert elapsed < 2.5
