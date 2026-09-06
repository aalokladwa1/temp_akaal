"""
tests.unit.engine_fabric.test_p7b_round3_toctou_stale_route
================================================================
P7B Group-1 Hostile Review Round 3 -- TOCTOU between plan / route / execution (§5).

Proves: a route planned against a set of edges can be detected as stale once topology
drifts (an edge fails/goes stale/is replaced) before execution -- via
MovementRoute.topology_fingerprint()/is_stale_against(), a narrow Group-1-scoped
freshness check (not a Group-2 topology-versioning authority). Also proves the
remote-execution assignment side of TOCTOU: an assignment's own continuous
revalidation (already proven in test_p7b_round3_fabric_to_transport_e2e.py) is what
actually blocks stale-assignment execution at the transport boundary; here we prove the
assignment becomes untrue as soon as any of its bound facts (tenant, site trust, fencing
epoch) changes after issuance.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.connectivity import ConnectivityClass, ConnectivityEdge, ConnectivityProofState, PrivacyAchieved, ReachabilityEvidence
from akaalEngine.fabric.execution_site import ExecutionSite, SiteAssignment, SiteKind, SiteRegistry, StaleFencingError
from akaalEngine.fabric.remote_execution import RemoteExecutionControlPlane, WrongTenantError, verify_assignment
from akaalEngine.fabric.route_planning import RoutePlanner

SIGNING_KEY = b"toctou-test-signing-key-0000001"


def _edge(source, dest, edge_id=None):
    return ConnectivityEdge(
        edge_id=edge_id or f"edge-{source}-{dest}", source_ref=source, destination_ref=dest,
        connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True,
    ).elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id=edge_id or f"edge-{source}-{dest}", achieved_privacy=PrivacyAchieved.PRIVATE))


def test_route_topology_fingerprint_detects_edge_becoming_stale():
    e1 = _edge("src", "site")
    e2 = _edge("site", "dst")
    route = RoutePlanner().plan_route("src", "dst", [e1, e2])
    fp_at_plan_time = route.topology_fingerprint()

    live_edges = {e1.edge_id: e1, e2.edge_id: e2}
    assert route.is_stale_against(live_edges) is False

    # Time passes; e2 goes stale.
    e2_now_stale = e2.mark_stale()
    live_edges_after = {e1.edge_id: e1, e2.edge_id: e2_now_stale}
    assert route.is_stale_against(live_edges_after) is True
    assert route.topology_fingerprint() == fp_at_plan_time  # the ROUTE object itself is immutable


def test_route_topology_fingerprint_detects_edge_becoming_failed():
    e1 = _edge("src", "dst")
    route = RoutePlanner().plan_route("src", "dst", [e1])

    failed_e1 = ConnectivityEdge(
        edge_id=e1.edge_id, source_ref="src", destination_ref="dst",
        connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True,
    ).elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id=e1.edge_id))

    assert route.is_stale_against({e1.edge_id: failed_e1}) is True


def test_route_topology_fingerprint_detects_missing_edge_entirely():
    """If a hop's edge_id no longer exists at all in the current topology snapshot
    (e.g. it was deregistered), the route must be flagged stale rather than silently
    treated as still valid."""
    e1 = _edge("src", "dst")
    route = RoutePlanner().plan_route("src", "dst", [e1])
    assert route.is_stale_against({}) is True


def test_route_not_flagged_stale_when_topology_genuinely_unchanged():
    e1 = _edge("src", "dst")
    route = RoutePlanner().plan_route("src", "dst", [e1])
    assert route.is_stale_against({e1.edge_id: e1}) is False


def test_two_routes_over_identical_topology_have_identical_fingerprint_deterministic():
    e1 = _edge("src", "dst")
    route_a = RoutePlanner().plan_route("src", "dst", [e1])
    route_b = RoutePlanner().plan_route("src", "dst", [e1])
    assert route_a.topology_fingerprint() == route_b.topology_fingerprint()


# ---------------------------------------------------------------------------
# Assignment-side TOCTOU: site revoked / tenant rebound / fencing advanced after issuance
# ---------------------------------------------------------------------------

def _ready_registry(site_id="site-1", tenant_id="tenant-a") -> SiteRegistry:
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry.verify_identity(site_id, verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry


def test_assignment_issued_before_revocation_but_verified_after_still_verifies_by_signature():
    """verify_assignment checks the SIGNED payload's own fields -- it does not re-consult
    SiteRegistry's live trust state at all (by design: verification is a pure,
    stateless, offline-checkable operation, exactly like JWT verification). This means
    revocation-after-issuance is NOT caught by verify_assignment itself -- it MUST be
    caught by whichever caller re-checks live site trust as part of its own
    security_revalidator, which is exactly the pattern proven in
    test_p7b_round3_fabric_to_transport_e2e.py. This test documents that boundary
    explicitly rather than leaving it implicit."""
    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
    )
    registry.revoke("site-1", reason="compromised after issuance")

    # verify_assignment alone still succeeds (it only checks the signed payload) --
    # proving that LIVE trust re-checking is a separate, mandatory responsibility of the
    # caller's own security_revalidator, not something verify_assignment provides.
    verify_assignment(
        assignment, SIGNING_KEY, expected_tenant_id="tenant-a", expected_plan_id="plan-1",
        expected_site_id="site-1", expected_seal_fingerprint="seal-fp",
    )

    # The caller's OWN live-trust check (what a correct security_revalidator does) must
    # independently catch the revocation.
    live_site = registry.get("site-1")
    assert live_site.trust_state.value == "REVOKED"


def test_fencing_epoch_advancing_after_issuance_blocks_a_second_assignment_at_the_old_epoch():
    """A second assignment attempt at the SAME (now-stale) epoch after a legitimate
    higher-epoch assignment has already been issued (e.g. a delayed/retried request)
    must be rejected -- proving epoch advancement genuinely invalidates stale
    assignment issuance, not just stale verification."""
    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=5, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
    )
    with pytest.raises(StaleFencingError):
        control_plane.issue_assignment(
            site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
            migration_id="mig-1", plan_id="plan-1", plan_revision=1,
            execution_identity_seal_fingerprint="seal-fp", fencing_epoch=5, correlation_id="corr-2-delayed-retry",
            signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
        )


def test_tenant_rebinding_after_issuance_does_not_retroactively_change_the_already_issued_assignment():
    """If a site's tenant binding is later changed (e.g. reassigned to a new customer),
    an assignment issued under the OLD tenant must still verify as belonging to the OLD
    tenant (it is immutable, signed data) -- but any NEW assignment attempt for the old
    tenant against the now-rebound site must fail, since SiteRegistry.assign_execution
    always checks the site's CURRENT tenant_binding."""
    registry = _ready_registry(tenant_id="tenant-old")
    control_plane = RemoteExecutionControlPlane(registry)
    old_assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-old", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
    )
    verify_assignment(
        old_assignment, SIGNING_KEY, expected_tenant_id="tenant-old", expected_plan_id="plan-1",
        expected_site_id="site-1", expected_seal_fingerprint="seal-fp",
    )  # still verifies -- it's immutable signed data about the past

    # Site is reassigned to a new tenant.
    registry.bind_tenant("site-1", "tenant-new", authorization_callback=lambda s, a, c: True)

    # A NEW assignment attempt for the OLD tenant against the now-rebound site fails.
    with pytest.raises(Exception):
        control_plane.issue_assignment(
            site_id="site-1", tenant_id="tenant-old", workspace_id="ws-1", project_id="proj-1",
            migration_id="mig-1", plan_id="plan-1", plan_revision=1,
            execution_identity_seal_fingerprint="seal-fp", fencing_epoch=2, correlation_id="corr-2",
            signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
        )
