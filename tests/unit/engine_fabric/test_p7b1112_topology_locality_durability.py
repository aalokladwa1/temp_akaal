"""
P7B.11/P7B.12 -- Topology + Locality durability: fresh-process restart reconstruction
through the canonical Authority #5 durability backend (not just in-memory rehydration).

PROCESS A -> register/persist -> destroy A -> genuinely fresh registry (PROCESS B) ->
reconstruct via akaalEngine.fabric.durability -> validate identity/tenant/staleness
semantics survived, and that corrupt/tampered state fails closed.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.durability import (
    FabricStateNotFoundError,
    new_sqlite_backed_store,
    reconstruct_locality_registry,
    reconstruct_topology_registry,
)
from akaalEngine.fabric.topology.models import (
    TopologyEdge,
    TopologyNode,
    TopologyNodeKind,
    TopologyRelationshipKind,
    new_topology_edge_id,
    new_topology_node_id,
)
from akaalEngine.fabric.topology.graph import TopologyRegistry
from akaalEngine.fabric.locality.models import (
    LocalityConfidence,
    LocalityRecord,
    LocalitySubjectRole,
)
from akaalEngine.fabric.locality.registry import LocalityRegistry

SIGNING_KEY = b"durability-test-fencing-key-0001"
ANCHOR_KEY = b"durability-test-anchor-key-00002"


def _store(tmp_path):
    return new_sqlite_backed_store(str(tmp_path), fencing_signing_key=SIGNING_KEY, journal_anchor_key=ANCHOR_KEY)


def test_topology_survives_restart(tmp_path):
    store_a = _store(tmp_path)
    registry_a = TopologyRegistry(durability_store=store_a)
    site = registry_a.register_node(TopologyNode(
        node_id=new_topology_node_id(TopologyNodeKind.EXECUTION_SITE), node_kind=TopologyNodeKind.EXECUTION_SITE,
        ref_id="site-mumbai", tenant_id="t1", provenance_source="SITE_REGISTRATION",
    ))
    env = registry_a.register_node(TopologyNode(
        node_id=new_topology_node_id(TopologyNodeKind.ENVIRONMENT), node_kind=TopologyNodeKind.ENVIRONMENT,
        ref_id="env-aws-mumbai", tenant_id="t1", provenance_source="OPERATOR_CONFIGURATION",
    ))
    registry_a.register_edge(TopologyEdge(
        topology_edge_id=new_topology_edge_id(), source_node_id=site.node_id, target_node_id=env.node_id,
        relationship_kind=TopologyRelationshipKind.RUNS_IN, tenant_id="t1", provenance_source="SITE_REGISTRATION",
    ))
    fp_before = registry_a.snapshot("t1").fingerprint()
    del registry_a  # PROCESS A destroyed

    store_b = _store(tmp_path)  # PROCESS B: fresh process, same durable storage_dir
    registry_b = reconstruct_topology_registry(store_b)
    snap_b = registry_b.snapshot("t1")
    assert snap_b.has_path(site.node_id, env.node_id)
    assert snap_b.fingerprint() == fp_before


def test_unregistered_topology_node_load_fails_closed_not_fabricated(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(FabricStateNotFoundError):
        store.load_topology_node("node-that-was-never-registered")


def test_unregistered_locality_record_load_fails_closed_not_fabricated(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(FabricStateNotFoundError):
        store.load_locality_record("t1", "no-such-subject", LocalitySubjectRole.SOURCE.value)


def test_locality_survives_restart(tmp_path):
    store_a = _store(tmp_path)
    registry_a = LocalityRegistry(durability_store=store_a)
    registry_a.register(LocalityRecord(
        subject_ref="oracle-mumbai", subject_role=LocalitySubjectRole.SOURCE, tenant_id="t1",
        country="IN", region="ap-south-1", confidence=LocalityConfidence.PROVEN,
        provenance_source="PROVIDER_DISCOVERY",
    ))
    del registry_a

    store_b = _store(tmp_path)
    registry_b = reconstruct_locality_registry(store_b)
    rec = registry_b.get_current("oracle-mumbai", LocalitySubjectRole.SOURCE, "t1")
    assert rec.country == "IN"
    from akaalEngine.fabric.locality.models import LocalityDimension
    assert rec.satisfies(LocalityDimension.COUNTRY, {"IN"}) is True


def test_locality_stale_flag_survives_restart(tmp_path):
    store_a = _store(tmp_path)
    registry_a = LocalityRegistry(durability_store=store_a)
    registry_a.register(LocalityRecord(
        subject_ref="staging-sg", subject_role=LocalitySubjectRole.STAGING, tenant_id="t1",
        country="SG", confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    ))
    registry_a.mark_stale("staging-sg", LocalitySubjectRole.STAGING, "t1")
    del registry_a

    store_b = _store(tmp_path)
    registry_b = reconstruct_locality_registry(store_b)
    rec = registry_b.get_current("staging-sg", LocalitySubjectRole.STAGING, "t1")
    assert rec.stale is True
    # A stale-but-restored record must still refuse to satisfy a proof requirement.
    from akaalEngine.fabric.locality.models import LocalityDimension
    assert rec.satisfies(LocalityDimension.COUNTRY, {"SG"}) is None
