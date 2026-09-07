"""
P7B.11 -- Canonical Topology Graph: positive, hostile, and integration tests.
"""

import pytest

from akaalEngine.fabric.topology.models import (
    TopologyEdge,
    TopologyNode,
    TopologyNodeKind,
    TopologyRelationshipKind,
    TopologyValidationError,
    new_topology_edge_id,
    new_topology_node_id,
)
from akaalEngine.fabric.topology.graph import (
    CrossTenantTopologyError,
    DuplicateTopologyEdgeIdentityError,
    DuplicateTopologyNodeIdentityError,
    TopologyRegistrationError,
    TopologyRegistry,
    UnknownTopologyEdgeError,
    UnknownTopologyNodeError,
)


def _node(kind, ref_id, tenant="t1", **kw):
    return TopologyNode(
        node_id=new_topology_node_id(kind),
        node_kind=kind,
        ref_id=ref_id,
        tenant_id=tenant,
        provenance_source=kw.pop("provenance_source", "OPERATOR_CONFIGURATION"),
        **kw,
    )


# ------------------------------------------------------------------ positive


def test_register_node_and_edge_builds_traversable_snapshot():
    reg = TopologyRegistry()
    env = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-1"))
    site = reg.register_node(_node(TopologyNodeKind.EXECUTION_SITE, "site-1"))
    edge = reg.register_edge(TopologyEdge(
        topology_edge_id=new_topology_edge_id(),
        source_node_id=site.node_id,
        target_node_id=env.node_id,
        relationship_kind=TopologyRelationshipKind.RUNS_IN,
        tenant_id="t1",
        provenance_source="SITE_REGISTRATION",
    ))
    snap = reg.snapshot("t1")
    assert snap.has_path(site.node_id, env.node_id)
    assert not snap.has_path(env.node_id, site.node_id)  # directed, not symmetric
    assert edge.topology_edge_id in {e.topology_edge_id for e in snap.edges()}


def test_snapshot_fingerprint_changes_on_mutation():
    reg = TopologyRegistry()
    n = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-1"))
    fp1 = reg.snapshot("t1").fingerprint()
    reg.mark_node_stale(n.node_id, "t1")
    fp2 = reg.snapshot("t1").fingerprint()
    assert fp1 != fp2


def test_is_stale_against_detects_drift():
    reg = TopologyRegistry()
    n = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-1"))
    snap1 = reg.snapshot("t1")
    reg.mark_node_stale(n.node_id, "t1")
    snap2 = reg.snapshot("t1")
    assert snap1.is_stale_against(snap2)
    assert not snap2.is_stale_against(reg.snapshot("t1"))


def test_stale_edges_excluded_from_traversal_by_default():
    reg = TopologyRegistry()
    a = reg.register_node(_node(TopologyNodeKind.EXECUTION_SITE, "site-a"))
    b = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-b"))
    edge = reg.register_edge(TopologyEdge(
        topology_edge_id=new_topology_edge_id(), source_node_id=a.node_id,
        target_node_id=b.node_id, relationship_kind=TopologyRelationshipKind.RUNS_IN,
        tenant_id="t1", provenance_source="SITE_REGISTRATION",
    ))
    assert reg.snapshot("t1").has_path(a.node_id, b.node_id)
    reg.mark_edge_stale(edge.topology_edge_id, "t1")
    snap = reg.snapshot("t1")
    assert not snap.has_path(a.node_id, b.node_id)
    assert snap.has_path(a.node_id, b.node_id, include_stale=True)


# ------------------------------------------------------------------ hostile: forged/duplicate identity


def test_duplicate_node_id_different_physical_ref_rejected():
    reg = TopologyRegistry()
    node = _node(TopologyNodeKind.ENVIRONMENT, "env-1")
    reg.register_node(node)
    forged = TopologyNode(
        node_id=node.node_id, node_kind=TopologyNodeKind.ENVIRONMENT, ref_id="env-EVIL",
        tenant_id="t1", provenance_source="UNKNOWN",
    )
    with pytest.raises(DuplicateTopologyNodeIdentityError):
        reg.register_node(forged)


def test_same_physical_ref_cannot_get_second_node_id():
    reg = TopologyRegistry()
    reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-1"))
    dup = _node(TopologyNodeKind.ENVIRONMENT, "env-1")  # same ref_id, fresh node_id
    with pytest.raises(DuplicateTopologyNodeIdentityError):
        reg.register_node(dup)


def test_duplicate_edge_id_different_endpoints_rejected():
    reg = TopologyRegistry()
    a = reg.register_node(_node(TopologyNodeKind.EXECUTION_SITE, "site-a"))
    b = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-b"))
    c = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-c"))
    eid = new_topology_edge_id()
    reg.register_edge(TopologyEdge(
        topology_edge_id=eid, source_node_id=a.node_id, target_node_id=b.node_id,
        relationship_kind=TopologyRelationshipKind.RUNS_IN, tenant_id="t1",
        provenance_source="SITE_REGISTRATION",
    ))
    with pytest.raises(DuplicateTopologyEdgeIdentityError):
        reg.register_edge(TopologyEdge(
            topology_edge_id=eid, source_node_id=a.node_id, target_node_id=c.node_id,
            relationship_kind=TopologyRelationshipKind.RUNS_IN, tenant_id="t1",
            provenance_source="SITE_REGISTRATION",
        ))


def test_edge_referencing_unregistered_node_rejected():
    reg = TopologyRegistry()
    a = reg.register_node(_node(TopologyNodeKind.EXECUTION_SITE, "site-a"))
    with pytest.raises(TopologyRegistrationError):
        reg.register_edge(TopologyEdge(
            topology_edge_id=new_topology_edge_id(), source_node_id=a.node_id,
            target_node_id="node-does-not-exist", relationship_kind=TopologyRelationshipKind.RUNS_IN,
            tenant_id="t1", provenance_source="SITE_REGISTRATION",
        ))


def test_self_loop_edge_rejected():
    with pytest.raises(TopologyValidationError):
        TopologyEdge(
            topology_edge_id=new_topology_edge_id(), source_node_id="n1", target_node_id="n1",
            relationship_kind=TopologyRelationshipKind.RUNS_IN, tenant_id="t1",
            provenance_source="SITE_REGISTRATION",
        )


def test_unknown_provenance_must_be_explicit_not_omitted():
    with pytest.raises(TopologyValidationError):
        TopologyNode(node_id="n1", node_kind=TopologyNodeKind.ENVIRONMENT, ref_id="env-1",
                     tenant_id="t1", provenance_source="")


# ------------------------------------------------------------------ hostile: cross-tenant


def test_cross_tenant_node_update_rejected():
    reg = TopologyRegistry()
    node = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-1", tenant="t1"))
    with pytest.raises(CrossTenantTopologyError):
        reg.update_node(node.node_id, "t2-attacker")


def test_cross_tenant_edge_construction_rejected():
    reg = TopologyRegistry()
    a = reg.register_node(_node(TopologyNodeKind.EXECUTION_SITE, "site-a", tenant="t1"))
    b = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-b", tenant="t1"))
    with pytest.raises(CrossTenantTopologyError):
        reg.register_edge(TopologyEdge(
            topology_edge_id=new_topology_edge_id(), source_node_id=a.node_id,
            target_node_id=b.node_id, relationship_kind=TopologyRelationshipKind.RUNS_IN,
            tenant_id="t2-attacker", provenance_source="SITE_REGISTRATION",
        ))


def test_snapshot_never_leaks_other_tenants_nodes():
    reg = TopologyRegistry()
    reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-1", tenant="t1"))
    reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-2", tenant="t2"))
    snap_t1 = reg.snapshot("t1")
    assert len(snap_t1.nodes()) == 1
    assert snap_t1.nodes()[0].ref_id == "env-1"


def test_get_node_cross_tenant_read_rejected():
    reg = TopologyRegistry()
    node = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-1", tenant="t1"))
    with pytest.raises(CrossTenantTopologyError):
        reg.get_node(node.node_id, "t2-attacker")


def test_mark_edge_stale_cross_tenant_rejected():
    reg = TopologyRegistry()
    a = reg.register_node(_node(TopologyNodeKind.EXECUTION_SITE, "site-a"))
    b = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-b"))
    edge = reg.register_edge(TopologyEdge(
        topology_edge_id=new_topology_edge_id(), source_node_id=a.node_id, target_node_id=b.node_id,
        relationship_kind=TopologyRelationshipKind.RUNS_IN, tenant_id="t1",
        provenance_source="SITE_REGISTRATION",
    ))
    with pytest.raises(CrossTenantTopologyError):
        reg.mark_edge_stale(edge.topology_edge_id, "t2-attacker")


# ------------------------------------------------------------------ hostile: unknown locators fail safely


def test_unknown_node_id_raises_not_fabricated():
    reg = TopologyRegistry()
    with pytest.raises(UnknownTopologyNodeError):
        reg.get_node("nope", "t1")
    snap = reg.snapshot("t1")
    with pytest.raises(UnknownTopologyNodeError):
        snap.node("nope")


def test_unknown_edge_id_raises_not_fabricated():
    reg = TopologyRegistry()
    snap = reg.snapshot("t1")
    with pytest.raises(UnknownTopologyEdgeError):
        snap.edge("nope")


def test_has_path_false_for_unknown_endpoints_not_error():
    reg = TopologyRegistry()
    n = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-1"))
    snap = reg.snapshot("t1")
    assert snap.has_path(n.node_id, "does-not-exist") is False
    assert snap.has_path("does-not-exist", n.node_id) is False


# ------------------------------------------------------------------ concurrency


def test_concurrent_node_registration_no_corruption():
    import threading

    reg = TopologyRegistry()
    errors = []

    def worker(i):
        try:
            reg.register_node(_node(TopologyNodeKind.RESOURCE, f"res-{i}", tenant="t1"))
        except Exception as exc:  # pragma: no cover - only fires on a real defect
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(64)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(reg.snapshot("t1").nodes()) == 64


# ------------------------------------------------------------------ restart reconstruction


def test_reconstruction_from_durable_records_rebuilds_graph():
    reg = TopologyRegistry()
    a = reg.register_node(_node(TopologyNodeKind.EXECUTION_SITE, "site-a"))
    b = reg.register_node(_node(TopologyNodeKind.ENVIRONMENT, "env-b"))
    edge = reg.register_edge(TopologyEdge(
        topology_edge_id=new_topology_edge_id(), source_node_id=a.node_id, target_node_id=b.node_id,
        relationship_kind=TopologyRelationshipKind.RUNS_IN, tenant_id="t1",
        provenance_source="SITE_REGISTRATION",
    ))

    fresh = TopologyRegistry()
    fresh._register_reconstructed_node(a)
    fresh._register_reconstructed_node(b)
    fresh._register_reconstructed_edge(edge)

    assert fresh.snapshot("t1").has_path(a.node_id, b.node_id)
    assert fresh.snapshot("t1").fingerprint() == reg.snapshot("t1").fingerprint()
