"""
akaalEngine.fabric.reachability.prober
=========================================
P7B.8 -- Network Path Discovery & Reachability.

Produces the ReachabilityEvidence that is the ONLY way to elevate a
akaalEngine.fabric.connectivity.ConnectivityEdge to PROVEN. This module performs a
real, minimal TCP-connect probe by default (dependency-injectable for tests), reusing
the same primitive akaalEngine.connection.probes.connectivity.ConnectivityProbe already
uses internally for its own TCP handshake step -- it does not reimplement TLS/auth/CDC
probing, which remains that module's job for a fully-specified EndpointSpec. This module
exists specifically for the pre-EndpointSpec, topology-level question: "is there a path
from A to B at all", asked about abstract environment/site pairs before a concrete
provider connection has been configured.

Never treats a configuration object (a ConnectivityEdge's declared class, a private
endpoint id, a route spec) as itself proof of reachability.
"""

from __future__ import annotations

import dataclasses
import socket
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from akaalEngine.fabric.connectivity.models import ConnectivityEdge, ConnectivityValidationError, ReachabilityEvidence


class ReachabilityFailureReason(str, Enum):
    """How a failed probe is classified -- callers must be able to distinguish these,
    never collapse them into one generic 'unreachable'."""
    DNS_FAILURE = "DNS_FAILURE"
    TIMEOUT = "TIMEOUT"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    TLS_FAILURE = "TLS_FAILURE"
    PROXY_FAILURE = "PROXY_FAILURE"
    BASTION_FAILURE = "BASTION_FAILURE"
    TUNNEL_FAILURE = "TUNNEL_FAILURE"
    BLOCKED_ROUTE = "BLOCKED_ROUTE"
    PROVIDER_API_FAILURE = "PROVIDER_API_FAILURE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ReachabilityProbeResult:
    evidence: ReachabilityEvidence
    failure_reason: Optional[ReachabilityFailureReason] = None


TCPProbeFn = Callable[[str, int, float], "ReachabilityProbeResult"]


def default_tcp_probe(host: str, port: int, timeout_seconds: float = 5.0) -> ReachabilityProbeResult:
    """Real minimal TCP-connect reachability probe. Distinguishes DNS failure, timeout,
    and connection-refused rather than reporting one generic failure."""
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            latency_ms = (time.perf_counter() - start) * 1000.0
            return ReachabilityProbeResult(
                evidence=ReachabilityEvidence(
                    probe_method="TCP_CONNECT",
                    succeeded=True,
                    bound_edge_id="UNBOUND",
                    latency_ms=latency_ms,
                    detail=f"TCP connect to {host}:{port} succeeded.",
                )
            )
    except socket.gaierror as exc:
        return ReachabilityProbeResult(
            evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND", detail=f"DNS resolution failed for {host}: {exc}"),
            failure_reason=ReachabilityFailureReason.DNS_FAILURE,
        )
    except socket.timeout:
        return ReachabilityProbeResult(
            evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND", detail=f"TCP connect to {host}:{port} timed out after {timeout_seconds}s."),
            failure_reason=ReachabilityFailureReason.TIMEOUT,
        )
    except ConnectionRefusedError as exc:
        return ReachabilityProbeResult(
            evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND", detail=f"Connection refused to {host}:{port}: {exc}"),
            failure_reason=ReachabilityFailureReason.CONNECTION_REFUSED,
        )
    except OSError as exc:
        return ReachabilityProbeResult(
            evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND", detail=f"TCP connect to {host}:{port} failed: {exc}"),
            failure_reason=ReachabilityFailureReason.UNKNOWN,
        )


class ReachabilityProber:
    """Coordinates probing an edge and producing the ReachabilityEvidence required to
    elevate/demote a ConnectivityEdge's proof_state."""

    def __init__(self, tcp_probe: TCPProbeFn = default_tcp_probe) -> None:
        self._tcp_probe = tcp_probe

    def probe_edge(self, edge: ConnectivityEdge, host: str, port: int, timeout_seconds: float = 5.0) -> ConnectivityEdge:
        result = self._tcp_probe(host, port, timeout_seconds)
        # Bind the evidence to THIS edge -- the tcp_probe function itself has no notion
        # of ConnectivityEdge, so binding happens here, at the one place that actually
        # knows which edge is being probed. This is what makes replaying evidence
        # produced for a different edge/host structurally impossible.
        bound_evidence = dataclasses.replace(result.evidence, bound_edge_id=edge.edge_id)
        return edge.elevate_to_proven(bound_evidence)

    def probe_bidirectional(
        self,
        edge: ConnectivityEdge,
        source_to_dest_host: str,
        source_to_dest_port: int,
        dest_to_source_host: Optional[str] = None,
        dest_to_source_port: Optional[int] = None,
        timeout_seconds: float = 5.0,
    ) -> "BidirectionalReachabilityResult":
        """Proves (or disproves) reachability in both directions independently -- source
        reachable + target unreachable, and vice versa, are genuinely distinct outcomes
        that must never be collapsed into a single boolean."""
        forward = self._tcp_probe(source_to_dest_host, source_to_dest_port, timeout_seconds)
        reverse = None
        if dest_to_source_host is not None and dest_to_source_port is not None:
            reverse = self._tcp_probe(dest_to_source_host, dest_to_source_port, timeout_seconds)

        overall_evidence = forward.evidence if (reverse is None or forward.evidence.succeeded == reverse.evidence.succeeded) else ReachabilityEvidence(
            probe_method="BIDIRECTIONAL_TCP_CONNECT",
            succeeded=False,
            bound_edge_id=edge.edge_id,
            detail="Asymmetric reachability: forward and reverse probes disagree.",
        )
        bound_evidence = dataclasses.replace(overall_evidence, bound_edge_id=edge.edge_id)
        return BidirectionalReachabilityResult(
            forward=forward,
            reverse=reverse,
            edge=edge.elevate_to_proven(bound_evidence),
        )


@dataclass(frozen=True)
class BidirectionalReachabilityResult:
    forward: ReachabilityProbeResult
    reverse: Optional[ReachabilityProbeResult]
    edge: ConnectivityEdge

    @property
    def is_asymmetric(self) -> bool:
        return self.reverse is not None and self.forward.evidence.succeeded != self.reverse.evidence.succeeded


default_reachability_prober = ReachabilityProber()
