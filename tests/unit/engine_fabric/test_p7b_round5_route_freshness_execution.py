"""
tests.unit.engine_fabric.test_p7b_round5_route_freshness_execution
=======================================================================
P7B Group-1 Hostile Closure Round 5 -- route freshness is now load-bearing.

Round 4 explicitly disclosed: `MovementRoute.topology_fingerprint()`/`is_stale_against()`
existed and were tested in isolation, but had NO production consumer -- "a helper nobody
calls is not a security control." This suite proves the Round-5 fix:
`execute_assignment_via_transport` now checks route freshness on every revalidation
point, and a topology mutation between planning and execution (or DURING multi-batch
execution) halts physical writes before any further external-boundary call.
"""

from __future__ import annotations

import csv

import pytest

from akaalEngine.fabric.connectivity import ConnectivityClass, ConnectivityEdge, PrivacyAchieved, ReachabilityEvidence
from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.remote_execution import RemoteExecutionControlPlane, RemoteExecutionError, execute_assignment_via_transport
from akaalEngine.fabric.route_planning import RoutePlanner
from akaalEngine.transport.api import TransportAuthority
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition
from akaalEngine.transport.models.errors import TransportFencingError

SIGNING_KEY = b"round5-route-freshness-key-00001"


def _proven_edge(edge_id, source, dest):
    return ConnectivityEdge(
        edge_id=edge_id, source_ref=source, destination_ref=dest,
        connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True,
    ).elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id=edge_id, achieved_privacy=PrivacyAchieved.PRIVATE))


def _ready_registry(site_id="site-1", tenant_id="tenant-a") -> SiteRegistry:
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry.verify_identity(site_id, verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry


def _setup(tmp_path):
    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
    )

    e1 = _proven_edge("e1", "src", "site-1")
    e2 = _proven_edge("e2", "site-1", "dst")
    route = RoutePlanner().plan_route("src", "dst", [e1, e2])

    source_csv = tmp_path / "source.csv"
    target_csv = tmp_path / "target.csv"
    with open(source_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id"])
        w.writeheader()
        w.writerow({"id": "1"})
        w.writerow({"id": "2"})

    transport_authority = TransportAuthority()
    reader = transport_authority.resolve_source_reader_for_provider("file", file_path=str(source_csv), format_type="CSV")
    writer = transport_authority.resolve_target_writer_for_provider("file", file_path=str(target_csv), format_type="CSV")
    partition = TransportPartition(partition_id="p0", table_name="source.csv", schema_name="file", target_schema="file", strategy=list(PartitionStrategy)[0])

    return registry, assignment, route, e1, e2, transport_authority, reader, writer, partition, target_csv


def test_unchanged_topology_executes_successfully(tmp_path):
    registry, assignment, route, e1, e2, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)
    live_edges = {e1.edge_id: e1, e2.edge_id: e2}

    rows_written = execute_assignment_via_transport(
        transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
        expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
        expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
        route=route, current_edges_provider=lambda: live_edges,
    )
    writer.close()
    assert rows_written == 2


def test_edge_removed_before_execution_blocks_all_physical_writes(tmp_path):
    """PLAN ROUTE -> edge deregistered -> EXECUTE -> reject before forbidden physical
    behavior. Zero rows must reach the target."""
    registry, assignment, route, e1, e2, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)
    live_edges_missing_e2 = {e1.edge_id: e1}  # e2 no longer exists in current topology

    with pytest.raises(TransportFencingError):
        execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
            expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
            route=route, current_edges_provider=lambda: live_edges_missing_e2,
        )
    writer.close()
    assert transport_authority.rows_written_total == 0
    with open(target_csv, encoding="utf-8") as fh:
        assert fh.read() == ""


def test_edge_becomes_stale_before_execution_blocks_execution(tmp_path):
    registry, assignment, route, e1, e2, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)
    e2_now_stale = e2.mark_stale()
    live_edges = {e1.edge_id: e1, e2.edge_id: e2_now_stale}

    with pytest.raises(TransportFencingError):
        execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
            expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
            route=route, current_edges_provider=lambda: live_edges,
        )
    writer.close()
    assert transport_authority.rows_written_total == 0


def test_edge_becomes_failed_before_execution_blocks_execution(tmp_path):
    registry, assignment, route, e1, e2, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)
    e2_failed = ConnectivityEdge(
        edge_id="e2", source_ref="site-1", destination_ref="dst",
        connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True,
    ).elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="e2"))
    live_edges = {e1.edge_id: e1, e2.edge_id: e2_failed}

    with pytest.raises(TransportFencingError):
        execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
            expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
            route=route, current_edges_provider=lambda: live_edges,
        )
    writer.close()
    assert transport_authority.rows_written_total == 0


def test_topology_mutating_mid_stream_halts_before_second_batch_write(tmp_path):
    """The genuinely continuous case: topology is FRESH for the first revalidation call
    (before the read loop starts) but mutates DURING execution (simulating a concurrent
    revocation/topology change while a multi-batch transfer is in flight). Because
    current_edges_provider is a live callable re-invoked on every one of
    TransportAuthority's existing revalidation points (not a one-shot snapshot), the
    mutation must be caught before further physical writes."""
    registry, assignment, route, e1, e2, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)

    state = {"edges": {e1.edge_id: e1, e2.edge_id: e2}, "calls": 0}

    def dynamic_current_edges():
        state["calls"] += 1
        if state["calls"] >= 2:
            # Topology mutates starting from the second revalidation call onward
            # (TransportAuthority calls security_revalidator before EVERY batch read).
            return {e1.edge_id: e1, e2.edge_id: e2.mark_stale()}
        return state["edges"]

    with pytest.raises(TransportFencingError):
        execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
            expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
            route=route, current_edges_provider=dynamic_current_edges,
        )
    writer.close()
    # The batch size in this test (2 rows) fits in a single TransportBatch, so the
    # mutation-on-second-call is caught at the pre-write/pre-commit revalidation point
    # for that same batch, before the row ever reaches the target file.
    assert transport_authority.rows_written_total == 0
    with open(target_csv, encoding="utf-8") as fh:
        assert fh.read() == ""
    assert state["calls"] >= 2  # proves the provider was genuinely re-invoked, not cached


def test_execute_without_route_context_is_unaffected_backward_compatible(tmp_path):
    """Callers who don't pass route/current_edges_provider (e.g. non-fabric-routed
    executions, or Round-4-era callers) are unaffected -- this is an additive,
    opt-in check, not a breaking requirement."""
    registry, assignment, route, e1, e2, transport_authority, reader, writer, partition, target_csv = _setup(tmp_path)

    rows_written = execute_assignment_via_transport(
        transport_authority=transport_authority, assignment=assignment, signing_key=SIGNING_KEY,
        expected_tenant_id="tenant-a", expected_plan_id="plan-1", expected_site_id="site-1",
        expected_seal_fingerprint="seal-fp", reader=reader, writer=writer, partition=partition,
        # no route / current_edges_provider supplied
    )
    writer.close()
    assert rows_written == 2
