"""
P7B.11 -- Topology Graph scale sanity. Measures actual local numbers; makes no
performance claims beyond what is measured here.
"""

import time

from akaalEngine.fabric.topology.models import (
    TopologyEdge,
    TopologyNode,
    TopologyNodeKind,
    TopologyRelationshipKind,
    new_topology_edge_id,
    new_topology_node_id,
)
from akaalEngine.fabric.topology.graph import TopologyRegistry


def test_thousands_of_nodes_and_edges_build_query_within_local_budget():
    reg = TopologyRegistry()
    node_count = 4000
    node_ids = []
    t0 = time.perf_counter()
    for i in range(node_count):
        n = reg.register_node(TopologyNode(
            node_id=new_topology_node_id(TopologyNodeKind.RESOURCE), node_kind=TopologyNodeKind.RESOURCE,
            ref_id=f"res-{i}", tenant_id="t1", provenance_source="PROVIDER_DISCOVERY",
        ))
        node_ids.append(n.node_id)
    build_nodes_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    for i in range(node_count - 1):
        reg.register_edge(TopologyEdge(
            topology_edge_id=new_topology_edge_id(), source_node_id=node_ids[i], target_node_id=node_ids[i + 1],
            relationship_kind=TopologyRelationshipKind.CONNECTED_VIA, tenant_id="t1",
            provenance_source="NETWORK_DISCOVERY",
        ))
    build_edges_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    snap = reg.snapshot("t1")
    snapshot_s = time.perf_counter() - t0

    assert len(snap.nodes()) == node_count
    assert len(snap.edges()) == node_count - 1

    t0 = time.perf_counter()
    reachable = snap.has_path(node_ids[0], node_ids[-1])
    traversal_s = time.perf_counter() - t0
    assert reachable is True

    # No hard perf assertion (measured local numbers only, per Group-2 truthfulness law
    # against fabricated performance claims) -- but this must complete, not hang, within
    # a generous local sanity ceiling.
    assert build_nodes_s + build_edges_s + snapshot_s + traversal_s < 30.0
