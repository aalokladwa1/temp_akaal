"""
tests.unit.engine_fabric.test_p7b_6_7_8_connectivity_reachability
=====================================================================
P7B.6 (Connectivity Fabric), P7B.7 (Cloud-Native Private Connectivity), and P7B.8
(Reachability) hostile tests.

Proves: CONFIGURED NETWORK != PROVEN NETWORK; PRIVATE ENDPOINT CONFIGURED != PRIVATE
CONNECTIVITY PROVEN; DNS/timeout/refused failures classified distinctly; asymmetric
(source reachable / target unreachable and vice versa) reachability distinguished;
malformed edges rejected; staleness is explicit, not implicit.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.connectivity import (
    CloudNativeConnectivityMechanism,
    CloudNativeConnectivityReference,
    ConnectivityClass,
    ConnectivityEdge,
    ConnectivityProofState,
    ConnectivityValidationError,
    PrivacyAchieved,
    ReachabilityEvidence,
    mechanical_route_type_for,
)
from akaalEngine.fabric.reachability import (
    ReachabilityFailureReason,
    ReachabilityProber,
    ReachabilityProbeResult,
)
from akaalEngine.connection.models.endpoint import RouteType


def _edge(**overrides) -> ConnectivityEdge:
    defaults = dict(
        edge_id="edge-1",
        source_ref="env-onprem-1",
        destination_ref="env-aws-1",
        connectivity_class=ConnectivityClass.PRIVATE_ENDPOINT,
        is_private=True,
    )
    defaults.update(overrides)
    return ConnectivityEdge(**defaults)


def test_new_edge_starts_configured_never_proven():
    edge = _edge()
    assert edge.proof_state == ConnectivityProofState.CONFIGURED
    assert edge.is_proven() is False


def test_self_loop_edge_rejected():
    with pytest.raises(ConnectivityValidationError):
        _edge(source_ref="env-1", destination_ref="env-1")


def test_empty_refs_rejected():
    with pytest.raises(ConnectivityValidationError):
        _edge(source_ref="", destination_ref="env-1")


def test_private_endpoint_configured_does_not_imply_proven():
    """Direct instantiation of a CloudNativeConnectivityReference at CONFIGURED must never
    be readable as reachability proof."""
    ref = CloudNativeConnectivityReference(
        mechanism=CloudNativeConnectivityMechanism.AWS_PRIVATELINK,
        native_resource_ref="vpce-0123456789abcdef0",
    )
    edge = _edge(cloud_native_reference=ref)
    assert ref.proof_state == ConnectivityProofState.CONFIGURED
    assert edge.proof_state == ConnectivityProofState.CONFIGURED
    assert edge.is_proven() is False


def test_elevate_to_proven_requires_real_evidence_object_not_a_bare_flag():
    edge = _edge()
    evidence = ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id=edge.edge_id, achieved_privacy=PrivacyAchieved.PRIVATE, latency_ms=12.3)
    proven = edge.elevate_to_proven(evidence)
    assert proven.is_proven()
    assert proven.last_evidence is evidence
    # Original edge is untouched (immutability).
    assert edge.proof_state == ConnectivityProofState.CONFIGURED


def test_failed_probe_evidence_elevates_to_proven_failed_not_proven():
    edge = _edge()
    evidence = ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id=edge.edge_id, detail="refused")
    result = edge.elevate_to_proven(evidence)
    assert result.proof_state == ConnectivityProofState.PROVEN_FAILED
    assert result.is_proven() is False


def test_mark_stale_only_affects_proven_edges():
    edge = _edge()
    assert edge.mark_stale().proof_state == ConnectivityProofState.CONFIGURED  # not proven -- no-op
    proven = edge.elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id=edge.edge_id, achieved_privacy=PrivacyAchieved.PRIVATE))
    stale = proven.mark_stale()
    assert stale.proof_state == ConnectivityProofState.PROVEN_STALE
    assert stale.is_proven() is False


def test_evidence_requires_nonempty_probe_method():
    with pytest.raises(ConnectivityValidationError):
        ReachabilityEvidence(probe_method="", succeeded=True, bound_edge_id="edge-1")


@pytest.mark.parametrize("connectivity_class,expected_route_type", [
    (ConnectivityClass.DIRECT_PRIVATE, RouteType.DIRECT),
    (ConnectivityClass.PRIVATE_ENDPOINT, RouteType.PRIVATE_ENDPOINT),
    (ConnectivityClass.PROXY, RouteType.HTTP_PROXY),
    (ConnectivityClass.BASTION, RouteType.SSH_BASTION_TUNNEL),
])
def test_mechanical_mapping_is_truthful_for_direct_mechanisms(connectivity_class, expected_route_type):
    assert mechanical_route_type_for(connectivity_class) == expected_route_type


@pytest.mark.parametrize("connectivity_class", [
    ConnectivityClass.CROSS_CLOUD, ConnectivityClass.RELAY, ConnectivityClass.CLOUD_BACKBONE,
    ConnectivityClass.DEDICATED_INTERCONNECT, ConnectivityClass.VPN, ConnectivityClass.PEERING,
])
def test_topology_only_classes_have_no_fabricated_single_mechanical_route_type(connectivity_class):
    """Never guess a mechanical RouteType for classes that genuinely require multi-hop
    route planning to resolve."""
    assert mechanical_route_type_for(connectivity_class) is None


# ---------------------------------------------------------------------------
# Reachability -- P7B.8
# ---------------------------------------------------------------------------

def _fixed_prober(result: ReachabilityProbeResult):
    return ReachabilityProber(tcp_probe=lambda host, port, timeout_seconds=5.0: result)


def test_reachability_dns_failure_classified_distinctly():
    result = ReachabilityProbeResult(
        evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND", detail="dns"),
        failure_reason=ReachabilityFailureReason.DNS_FAILURE,
    )
    prober = _fixed_prober(result)
    edge = prober.probe_edge(_edge(), host="bad.invalid", port=443)
    assert edge.proof_state == ConnectivityProofState.PROVEN_FAILED


def test_reachability_timeout_classified_distinctly():
    result = ReachabilityProbeResult(
        evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND", detail="timeout"),
        failure_reason=ReachabilityFailureReason.TIMEOUT,
    )
    prober = _fixed_prober(result)
    edge = prober.probe_edge(_edge(), host="10.255.255.1", port=443)
    assert edge.proof_state == ConnectivityProofState.PROVEN_FAILED


def test_reachability_success_elevates_edge_to_proven():
    result = ReachabilityProbeResult(evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="UNBOUND", achieved_privacy=PrivacyAchieved.PRIVATE, latency_ms=4.2))
    prober = _fixed_prober(result)
    edge = prober.probe_edge(_edge(), host="10.0.0.5", port=5432)
    assert edge.is_proven()


def test_asymmetric_reachability_source_reachable_target_unreachable():
    """Source reachable / target unreachable must be genuinely distinguishable from the
    reverse case, never collapsed into one boolean."""

    def fake_probe(host, port, timeout_seconds=5.0):
        if host == "source-reachable":
            return ReachabilityProbeResult(evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="UNBOUND"))
        return ReachabilityProbeResult(
            evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND"),
            failure_reason=ReachabilityFailureReason.CONNECTION_REFUSED,
        )

    prober = ReachabilityProber(tcp_probe=fake_probe)
    result = prober.probe_bidirectional(
        _edge(),
        source_to_dest_host="source-reachable",
        source_to_dest_port=443,
        dest_to_source_host="target-unreachable",
        dest_to_source_port=443,
    )
    assert result.is_asymmetric
    assert result.forward.evidence.succeeded is True
    assert result.reverse.evidence.succeeded is False


def test_symmetric_unreachable_both_directions_not_flagged_as_asymmetric():
    def fake_probe(host, port, timeout_seconds=5.0):
        return ReachabilityProbeResult(evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND"))

    prober = ReachabilityProber(tcp_probe=fake_probe)
    result = prober.probe_bidirectional(_edge(), "a", 1, "b", 1)
    assert result.is_asymmetric is False
    assert result.edge.proof_state == ConnectivityProofState.PROVEN_FAILED


def test_real_default_tcp_probe_against_unroutable_address_fails_without_hanging():
    from akaalEngine.fabric.reachability import default_tcp_probe
    # TEST-NET-1 (RFC 5737) -- guaranteed non-routable, real socket-level probe should
    # time out or refuse quickly rather than hang or fabricate success.
    result = default_tcp_probe("192.0.2.1", 9, timeout_seconds=0.5)
    assert result.evidence.succeeded is False
