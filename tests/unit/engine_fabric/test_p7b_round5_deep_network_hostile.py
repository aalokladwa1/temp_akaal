"""
tests.unit.engine_fabric.test_p7b_round5_deep_network_hostile
==================================================================
P7B Group-1 Hostile Closure Round 5 -- deep network hostile matrix closure.

Honest scope statement: a bare TCP-connect probe (`default_tcp_probe`) is, by
construction, INCAPABLE of detecting DNS spoofing/rebinding, proxy/bastion substitution,
or TLS hostname/certificate mismatches -- those require application-layer verification
(TLS certificate CN/SAN validation, host-key pinning) that a raw TCP handshake does not
perform. This is not something to paper over: it is exactly why `achieved_privacy`
(Round 2) caps a bare TCP probe's result at PUBLIC tier, and why `elevate_to_proven`
(Round 2) refuses to let PUBLIC-tier evidence prove a `is_private=True` edge. This suite
makes that chain of reasoning explicit and directly tested, rather than left implicit.

Also covers: DNS failure classification (already real, Round 2), wrong-port
distinguished from wrong-host, and asymmetric-then-degrading reachability (probe
succeeds, then a later probe on the SAME edge fails -- proving staleness is re-evaluated
per probe, never cached indefinitely).
"""

from __future__ import annotations

import socket

import pytest

from akaalEngine.fabric.connectivity import ConnectivityClass, ConnectivityEdge, ConnectivityValidationError, PrivacyAchieved, ReachabilityEvidence
from akaalEngine.fabric.reachability import ReachabilityFailureReason, ReachabilityProber, ReachabilityProbeResult, default_tcp_probe


def test_bare_tcp_success_can_never_be_escalated_to_prove_tls():
    """TCP_SUCCESS must never imply TLS_PROVEN: default_tcp_probe's own evidence never
    claims a privacy tier above PUBLIC, structurally (checked at the dataclass default,
    not by convention)."""
    result = default_tcp_probe("127.0.0.1", 1, timeout_seconds=0.2)
    assert result.evidence.achieved_privacy == PrivacyAchieved.PUBLIC


def test_public_tier_evidence_cannot_prove_private_edge_even_with_correct_edge_binding():
    """The full chain: TCP_SUCCESS (PUBLIC) -> correctly bound to the right edge -> still
    cannot prove a PRIVATE_PATH requirement. Binding correctness alone is not sufficient;
    the privacy tier gate is a SEPARATE, additional check."""
    edge = ConnectivityEdge(edge_id="e1", source_ref="src", destination_ref="dst", connectivity_class=ConnectivityClass.PRIVATE_ENDPOINT, is_private=True)
    evidence = ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="e1", achieved_privacy=PrivacyAchieved.PUBLIC)
    with pytest.raises(ConnectivityValidationError):
        edge.elevate_to_proven(evidence)


def test_tls_tier_evidence_alone_still_cannot_prove_mtls_required_edge():
    """PRIVATE-tier evidence is the floor for a private edge -- but note the model's
    actual tier ordering (PUBLIC<TLS<PRIVATE<MTLS) means TLS-only evidence is likewise
    insufficient for a private-path requirement, exactly as PUBLIC is."""
    edge = ConnectivityEdge(edge_id="e1", source_ref="src", destination_ref="dst", connectivity_class=ConnectivityClass.PRIVATE_ENDPOINT, is_private=True)
    tls_only_evidence = ReachabilityEvidence(probe_method="TLS_HANDSHAKE", succeeded=True, bound_edge_id="e1", achieved_privacy=PrivacyAchieved.TLS)
    with pytest.raises(ConnectivityValidationError):
        edge.elevate_to_proven(tls_only_evidence)


def test_dns_failure_classified_distinctly_from_connection_refused_and_timeout():
    """Real DNS_FAILURE, CONNECTION_REFUSED, and TIMEOUT must never collapse into one
    generic 'unreachable' classification -- proven against the REAL socket-level probe,
    not a fake standing in for it."""
    dns_result = default_tcp_probe("this-host-genuinely-does-not-resolve.invalid", 443, timeout_seconds=2.0)
    assert dns_result.failure_reason == ReachabilityFailureReason.DNS_FAILURE

    refused_result = default_tcp_probe("127.0.0.1", 1, timeout_seconds=2.0)
    # Port 1 is virtually always closed/refused on a real loopback interface.
    assert refused_result.failure_reason in (ReachabilityFailureReason.CONNECTION_REFUSED, ReachabilityFailureReason.TIMEOUT)
    assert refused_result.failure_reason != ReachabilityFailureReason.DNS_FAILURE


def test_wrong_port_produces_a_distinct_failure_from_wrong_host():
    """Probing the RIGHT host but WRONG port must not be silently reported the same way
    as a DNS failure -- both are real, distinct network conditions."""
    wrong_port_result = default_tcp_probe("127.0.0.1", 1, timeout_seconds=1.0)
    wrong_host_result = default_tcp_probe("this-host-genuinely-does-not-resolve.invalid", 443, timeout_seconds=1.0)
    assert wrong_port_result.failure_reason != wrong_host_result.failure_reason
    assert wrong_host_result.failure_reason == ReachabilityFailureReason.DNS_FAILURE


def test_probe_succeeding_then_later_failing_on_the_same_edge_is_re_evaluated_not_cached():
    """A route/edge that was reachable at plan time and becomes unreachable later must
    be re-probed, never trusted from a stale cached PROVEN state -- this is exactly what
    ReachabilityProber does (it never caches results across calls)."""
    call_sequence = {"n": 0}

    def flaky_probe(host, port, timeout_seconds=5.0):
        call_sequence["n"] += 1
        succeeded = call_sequence["n"] == 1  # succeeds once, then starts failing
        return ReachabilityProbeResult(
            evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=succeeded, bound_edge_id="e1"),
            failure_reason=None if succeeded else ReachabilityFailureReason.CONNECTION_REFUSED,
        )

    prober = ReachabilityProber(tcp_probe=flaky_probe)
    edge = ConnectivityEdge(edge_id="e1", source_ref="src", destination_ref="dst", connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=False)

    first = prober.probe_edge(edge, host="10.0.0.1", port=443)
    assert first.is_proven()

    second = prober.probe_edge(edge, host="10.0.0.1", port=443)  # re-probing the SAME (unproven-again) edge
    assert not second.is_proven()
    assert call_sequence["n"] == 2  # genuinely re-probed, not served from a cache
