"""
tests.unit.engine_fabric.test_p7b_round2_evidence_provenance
=================================================================
P7B Group-1 Hostile Review Round 2 -- ReachabilityEvidence provenance hardening (§7).

The first pass let ANY caller construct `ReachabilityEvidence(succeeded=True)` and feed
it into `edge.elevate_to_proven()` with no binding to which edge/endpoint was actually
probed, and no declaration of what privacy tier was achieved. This suite proves the
Round-2 fix: evidence is now bound to a specific edge_id and declares an achieved
privacy tier, and elevate_to_proven refuses evidence that doesn't genuinely apply.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.connectivity import (
    ConnectivityClass,
    ConnectivityEdge,
    ConnectivityProofState,
    ConnectivityValidationError,
    PrivacyAchieved,
    ReachabilityEvidence,
)
from akaalEngine.fabric.reachability import ReachabilityProber, ReachabilityProbeResult


def _private_edge(edge_id="edge-target") -> ConnectivityEdge:
    return ConnectivityEdge(
        edge_id=edge_id, source_ref="src", destination_ref="dst",
        connectivity_class=ConnectivityClass.PRIVATE_ENDPOINT, is_private=True,
    )


def test_evidence_requires_bound_edge_id():
    with pytest.raises(ConnectivityValidationError):
        ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="")


def test_evidence_from_another_edge_cannot_prove_this_edge():
    """Attack: fabricate evidence claiming success, bound to a DIFFERENT edge than the
    one being elevated -- must be refused, not silently accepted."""
    target_edge = _private_edge("edge-target")
    evidence_for_other_edge = ReachabilityEvidence(
        probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="edge-completely-different",
        achieved_privacy=PrivacyAchieved.PRIVATE,
    )
    with pytest.raises(ConnectivityValidationError):
        target_edge.elevate_to_proven(evidence_for_other_edge)


def test_evidence_from_another_route_or_tenant_cannot_be_replayed():
    """Same underlying protection, phrased as the cross-tenant/cross-route replay
    attack: an attacker who legitimately proved tenant A's edge cannot reuse that exact
    evidence object to "prove" tenant B's edge, because edge_ids differ."""
    tenant_a_edge = _private_edge("tenant-a-edge")
    tenant_b_edge = _private_edge("tenant-b-edge")

    genuine_evidence_for_a = ReachabilityEvidence(
        probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="tenant-a-edge", achieved_privacy=PrivacyAchieved.PRIVATE,
    )
    proven_a = tenant_a_edge.elevate_to_proven(genuine_evidence_for_a)
    assert proven_a.is_proven()

    with pytest.raises(ConnectivityValidationError):
        tenant_b_edge.elevate_to_proven(genuine_evidence_for_a)  # replay attempt


def test_public_probe_cannot_prove_private_endpoint():
    """PRIVATE ENDPOINT CONFIGURED != PRIVATE CONNECTIVITY PROVEN: a successful probe
    that only achieved PUBLIC-tier connectivity must never elevate a private-required
    edge to PROVEN."""
    edge = _private_edge()
    public_evidence = ReachabilityEvidence(
        probe_method="TCP_CONNECT", succeeded=True, bound_edge_id=edge.edge_id, achieved_privacy=PrivacyAchieved.PUBLIC,
    )
    with pytest.raises(ConnectivityValidationError):
        edge.elevate_to_proven(public_evidence)


def test_tls_only_probe_cannot_prove_mtls_or_private_requirement():
    """TLS path used to "prove" mTLS/private connectivity -- must be refused."""
    edge = _private_edge()
    tls_only_evidence = ReachabilityEvidence(
        probe_method="TLS_HANDSHAKE", succeeded=True, bound_edge_id=edge.edge_id, achieved_privacy=PrivacyAchieved.TLS,
    )
    with pytest.raises(ConnectivityValidationError):
        edge.elevate_to_proven(tls_only_evidence)


def test_private_evidence_correctly_proves_private_edge():
    """The converse -- genuine PRIVATE-tier evidence, correctly bound, DOES succeed."""
    edge = _private_edge()
    real_evidence = ReachabilityEvidence(
        probe_method="PRIVATE_ENDPOINT_HANDSHAKE", succeeded=True, bound_edge_id=edge.edge_id, achieved_privacy=PrivacyAchieved.PRIVATE,
    )
    proven = edge.elevate_to_proven(real_evidence)
    assert proven.is_proven()


def test_non_private_edge_accepts_public_tier_evidence():
    """A non-private edge (e.g. PUBLIC_TLS class) should NOT be held to the private-tier
    requirement -- only `is_private=True` edges are."""
    edge = ConnectivityEdge(
        edge_id="public-edge", source_ref="src", destination_ref="dst",
        connectivity_class=ConnectivityClass.PUBLIC_TLS, is_private=False,
    )
    evidence = ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="public-edge", achieved_privacy=PrivacyAchieved.PUBLIC)
    proven = edge.elevate_to_proven(evidence)
    assert proven.is_proven()


def test_failed_probe_never_triggers_privacy_check_even_for_private_edge():
    """A FAILED probe on a private edge must produce PROVEN_FAILED (not raise a privacy
    error) -- the privacy-tier check only applies to claimed successes."""
    edge = _private_edge()
    failed_evidence = ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id=edge.edge_id)
    result = edge.elevate_to_proven(failed_evidence)
    assert result.proof_state == ConnectivityProofState.PROVEN_FAILED


def test_reachability_prober_always_binds_evidence_to_the_actual_edge_being_probed():
    """Even if the injected tcp_probe function returns evidence bound to the wrong (or
    no) edge, ReachabilityProber.probe_edge rebinds it to the REAL edge before
    elevation -- proving the binding authority lives at the one place that actually
    knows which edge is being probed, not with the (possibly untrusted/generic) probe
    function."""
    def careless_probe(host, port, timeout_seconds=5.0):
        # Returns evidence "bound" to a bogus id -- the prober must correct this.
        return ReachabilityProbeResult(evidence=ReachabilityEvidence(
            probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="whatever-i-felt-like",
            achieved_privacy=PrivacyAchieved.PRIVATE,
        ))

    prober = ReachabilityProber(tcp_probe=careless_probe)
    edge = _private_edge("the-real-edge")
    proven = prober.probe_edge(edge, host="10.0.0.1", port=443)
    assert proven.is_proven()
    assert proven.last_evidence.bound_edge_id == "the-real-edge"


def test_evidence_freshness_helper_distinguishes_fresh_from_stale():
    from datetime import datetime, timedelta, timezone
    old_evidence = ReachabilityEvidence(
        probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="e1",
        probed_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
    )
    assert old_evidence.is_fresh(max_age_seconds=60) is False
    assert old_evidence.is_fresh(max_age_seconds=3 * 3600) is True
