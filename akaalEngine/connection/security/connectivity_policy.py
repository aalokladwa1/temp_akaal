"""akaalEngine.connection.security.connectivity_policy
====================================================
P7.9 Encryption-Aware Migration / Connectivity Policy Enforcement.

Given a canonical connectivity requirement (a policy VALUE decided upstream by
akaalPipeline/operator configuration and carried down as data on
EndpointSpec.required_connectivity_tier -- never invented here, never a UI checkbox),
validates that a physical connection's actual TLSBinding/RouteSpec genuinely satisfies
it BEFORE Engine is permitted to establish the physical connection. A migration that
requires a protected channel must never silently run over an unprotected one.

Architectural placement note: this module lives in akaalEngine (not akaalPipeline)
because it operates exclusively on Engine's own physical connection descriptor types
(TLSBinding/RouteSpec) and is invoked directly on Engine's authoritative connection-
establishment path (akaalEngine.connection.sessions.factory.SessionFactory). Engine
enforces the policy value; it does not decide what the value should be -- that remains
Pipeline's / the operator's responsibility, expressed as configuration data.

This module performs no network I/O itself (that remains
akaalEngine.connection.security.tls / .routing.ssh / .routing.proxy's job); it only
evaluates policy against already-real connection descriptor objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from akaalEngine.connection.models.endpoint import RouteSpec, RouteType, TLSBinding, TLSMode


class ConnectivityRequirement(str, Enum):
    """Ordered minimum connectivity protection tiers, from weakest to strongest."""
    NONE = "NONE"
    TLS = "TLS"
    MTLS = "MTLS"
    TUNNEL = "TUNNEL"
    PRIVATE_PATH = "PRIVATE_PATH"


_TIER_RANK = {
    ConnectivityRequirement.NONE: 0,
    ConnectivityRequirement.TLS: 1,
    ConnectivityRequirement.MTLS: 2,
    ConnectivityRequirement.TUNNEL: 3,
    ConnectivityRequirement.PRIVATE_PATH: 4,
}


class ConnectivityPolicyViolationError(ValueError):
    """Raised when the actual connection descriptor does not satisfy the required protection tier."""


@dataclass(frozen=True)
class ConnectivityComplianceReport:
    satisfied: bool
    required: ConnectivityRequirement
    achieved_tier: ConnectivityRequirement
    reason: str


class ConnectivityPolicyEnforcer:
    """Canonical fail-closed evaluator of encryption/connectivity requirements against real connection descriptors."""

    def evaluate(
        self,
        required: ConnectivityRequirement,
        tls_binding: Optional[TLSBinding],
        route_spec: Optional[RouteSpec],
    ) -> ConnectivityComplianceReport:
        achieved = self._achieved_tier(tls_binding, route_spec)
        satisfied = _TIER_RANK[achieved] >= _TIER_RANK[required]
        reason = (
            f"Connection achieves {achieved.value!r} protection, satisfying required {required.value!r}."
            if satisfied
            else f"Connection only achieves {achieved.value!r} protection; policy requires >= {required.value!r}."
        )
        return ConnectivityComplianceReport(satisfied=satisfied, required=required, achieved_tier=achieved, reason=reason)

    def enforce(
        self,
        required: ConnectivityRequirement,
        tls_binding: Optional[TLSBinding],
        route_spec: Optional[RouteSpec],
    ) -> ConnectivityComplianceReport:
        """Fail-closed: raises ConnectivityPolicyViolationError if the requirement is not met."""
        report = self.evaluate(required, tls_binding, route_spec)
        if not report.satisfied:
            raise ConnectivityPolicyViolationError(report.reason)
        return report

    @staticmethod
    def _achieved_tier(tls_binding: Optional[TLSBinding], route_spec: Optional[RouteSpec]) -> ConnectivityRequirement:
        # Private path: an already-provisioned private endpoint is being consumed.
        if route_spec and route_spec.route_type == RouteType.PRIVATE_ENDPOINT and route_spec.private_endpoint_id:
            return ConnectivityRequirement.PRIVATE_PATH

        # Tunnel: SSH bastion with real, non-permissive host-key verification, or a
        # forward/reverse proxy route explicitly selected.
        if route_spec and route_spec.route_type == RouteType.SSH_BASTION_TUNNEL and route_spec.ssh_host:
            host_verified = bool(route_spec.ssh_known_hosts_path or route_spec.ssh_host_key_fingerprint)
            if host_verified and not route_spec.allow_unverified_ssh:
                return ConnectivityRequirement.TUNNEL
            # Unverified SSH tunnels do not count toward the TUNNEL protection tier --
            # fail closed to TLS-only evaluation below rather than crediting a weak tunnel.

        # mTLS: strict TLS mode AND a client certificate configured for mutual auth.
        if tls_binding and tls_binding.mode in (TLSMode.VERIFY_CA, TLSMode.VERIFY_FULL):
            if tls_binding.client_cert_path or tls_binding.client_key_ref:
                return ConnectivityRequirement.MTLS
            return ConnectivityRequirement.TLS

        if tls_binding and tls_binding.mode == TLSMode.REQUIRED:
            return ConnectivityRequirement.TLS

        return ConnectivityRequirement.NONE
