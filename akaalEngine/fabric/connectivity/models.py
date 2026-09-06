"""
akaalEngine.fabric.connectivity.models
=========================================
P7B.6 -- Connectivity Fabric, and P7B.7 -- Cloud-Native Private Connectivity.

Provider-neutral representation of how two locations (environments / execution sites)
can communicate, layered ABOVE the existing physical routing primitives
(akaalEngine.connection.models.endpoint.RouteType/RouteSpec, which remain the
authoritative mechanics for actually establishing a connection) -- this module
represents topology-level connectivity *declarations*, never a second transport engine.

Absolute law: CONFIGURED NETWORK != PROVEN NETWORK. A `ConnectivityEdge` starts life at
`ConnectivityProofState.CONFIGURED` and can only reach `PROVEN` through
`elevate_to_proven`, which requires actual `ReachabilityEvidence` (see
akaalEngine.fabric.reachability) -- never a bare flag flip.

This is also the proper home for the previously explicitly-deferred SSH/bastion/proxy/VPN
enterprise-connectivity scope (see akaalEngine.connection.routing.private_connectivity's
module docstring, which names this exact P7B platform as the intended home).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, Optional
from types import MappingProxyType

from akaalEngine.connection.models.endpoint import RouteType


class ConnectivityClass(str, Enum):
    """Topology-level connectivity classification -- distinct from (but mappable to) the
    connection-mechanical akaalEngine.connection.models.endpoint.RouteType."""
    DIRECT_PRIVATE = "DIRECT_PRIVATE"
    PRIVATE_ENDPOINT = "PRIVATE_ENDPOINT"
    DEDICATED_INTERCONNECT = "DEDICATED_INTERCONNECT"
    VPN = "VPN"
    PEERING = "PEERING"
    PROXY = "PROXY"
    BASTION = "BASTION"
    SSH_TUNNEL = "SSH_TUNNEL"
    PUBLIC_TLS = "PUBLIC_TLS"
    CLOUD_BACKBONE = "CLOUD_BACKBONE"
    CROSS_CLOUD = "CROSS_CLOUD"
    RELAY = "RELAY"


# Deterministic, honest mapping to the mechanical route types that actually exist today.
# CROSS_CLOUD/RELAY/CLOUD_BACKBONE/DEDICATED_INTERCONNECT/VPN/PEERING have no single
# universal RouteType equivalent -- they describe topology, not a socket-level mechanism
# -- and truthfully map to None (the route planner must select a concrete mechanical
# RouteType per hop; see akaalEngine.fabric.route_planning).
_CONNECTIVITY_CLASS_TO_ROUTE_TYPE: Mapping[ConnectivityClass, Optional[RouteType]] = {
    ConnectivityClass.DIRECT_PRIVATE: RouteType.DIRECT,
    ConnectivityClass.PRIVATE_ENDPOINT: RouteType.PRIVATE_ENDPOINT,
    ConnectivityClass.PROXY: RouteType.HTTP_PROXY,
    ConnectivityClass.BASTION: RouteType.SSH_BASTION_TUNNEL,
    ConnectivityClass.SSH_TUNNEL: RouteType.SSH_BASTION_TUNNEL,
    ConnectivityClass.PUBLIC_TLS: RouteType.DNS_HAPPY_EYEBALLS,
    ConnectivityClass.DEDICATED_INTERCONNECT: None,
    ConnectivityClass.VPN: None,
    ConnectivityClass.PEERING: None,
    ConnectivityClass.CLOUD_BACKBONE: None,
    ConnectivityClass.CROSS_CLOUD: None,
    ConnectivityClass.RELAY: None,
}


def mechanical_route_type_for(connectivity_class: ConnectivityClass) -> Optional[RouteType]:
    """Truthful, deterministic mapping -- returns None rather than guessing when no
    single mechanical RouteType corresponds to a purely topological connectivity class."""
    return _CONNECTIVITY_CLASS_TO_ROUTE_TYPE[connectivity_class]


class ConnectivityProofState(str, Enum):
    CONFIGURED = "CONFIGURED"
    PROVEN = "PROVEN"
    PROVEN_STALE = "PROVEN_STALE"
    PROVEN_FAILED = "PROVEN_FAILED"


class CloudNativeConnectivityMechanism(str, Enum):
    """Real, provider-native private-connectivity mechanisms this fabric can reference and
    validate -- never reimplements the underlying cloud networking product."""
    AWS_VPC_ENDPOINT = "AWS_VPC_ENDPOINT"
    AWS_PRIVATELINK = "AWS_PRIVATELINK"
    AWS_TRANSIT_GATEWAY = "AWS_TRANSIT_GATEWAY"
    AWS_VPN = "AWS_VPN"
    AWS_DIRECT_CONNECT = "AWS_DIRECT_CONNECT"
    AZURE_PRIVATE_LINK = "AZURE_PRIVATE_LINK"
    AZURE_PRIVATE_ENDPOINT = "AZURE_PRIVATE_ENDPOINT"
    AZURE_VNET_PEERING = "AZURE_VNET_PEERING"
    AZURE_VPN_GATEWAY = "AZURE_VPN_GATEWAY"
    AZURE_EXPRESSROUTE = "AZURE_EXPRESSROUTE"
    GCP_PRIVATE_SERVICE_CONNECT = "GCP_PRIVATE_SERVICE_CONNECT"
    GCP_VPC_PEERING = "GCP_VPC_PEERING"
    GCP_CLOUD_VPN = "GCP_CLOUD_VPN"
    GCP_CLOUD_INTERCONNECT = "GCP_CLOUD_INTERCONNECT"
    OCI_SERVICE_GATEWAY = "OCI_SERVICE_GATEWAY"
    OCI_PRIVATE_ENDPOINT = "OCI_PRIVATE_ENDPOINT"
    OCI_DRG = "OCI_DRG"
    OCI_VPN = "OCI_VPN"
    OCI_FASTCONNECT = "OCI_FASTCONNECT"


class ConnectivityValidationError(ValueError):
    pass


class PrivacyAchieved(str, Enum):
    """Ordered, from weakest to strongest, exactly like
    akaalEngine.connection.security.connectivity_policy.ConnectivityRequirement (whose
    vocabulary this deliberately mirrors so the two tiers stay comparable) -- what a
    reachability probe actually verified about the path, not what was merely requested."""
    PUBLIC = "PUBLIC"
    TLS = "TLS"
    PRIVATE = "PRIVATE"
    MTLS = "MTLS"


_PRIVACY_RANK = {PrivacyAchieved.PUBLIC: 0, PrivacyAchieved.TLS: 1, PrivacyAchieved.PRIVATE: 2, PrivacyAchieved.MTLS: 3}


@dataclass(frozen=True)
class ReachabilityEvidence:
    """
    The ONLY thing that can elevate a ConnectivityEdge to PROVEN. Always carries a real
    probe method + timestamp; never a bare boolean.

    Round-2 hostile-review hardening (P7B Group-1 §7): evidence is now bound to the
    SPECIFIC edge it was produced for (`bound_edge_id`) and declares what privacy tier
    the probe actually achieved (`achieved_privacy`) -- this closes two real attack
    classes the first pass left open:
      1. Evidence produced for one edge/route/endpoint being replayed to "prove" a
         completely different edge (ConnectivityEdge.elevate_to_proven now verifies
         `evidence.bound_edge_id == self.edge_id` and refuses otherwise).
      2. A merely-public or TLS-only probe result being used to "prove" a PRIVATE_PATH
         edge -- ConnectivityEdge.elevate_to_proven now refuses to elevate a `is_private`
         edge using evidence whose achieved_privacy is only PUBLIC/TLS.
    """
    probe_method: str
    succeeded: bool
    bound_edge_id: str
    achieved_privacy: PrivacyAchieved = PrivacyAchieved.PUBLIC
    probed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latency_ms: Optional[float] = None
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.probe_method or not self.probe_method.strip():
            raise ConnectivityValidationError("ReachabilityEvidence.probe_method must be non-empty.")
        if not self.bound_edge_id or not self.bound_edge_id.strip():
            raise ConnectivityValidationError(
                "ReachabilityEvidence.bound_edge_id must be non-empty -- evidence must "
                "always declare which specific edge it was produced for; unbound "
                "evidence could otherwise be replayed onto an unrelated edge."
            )

    def is_fresh(self, max_age_seconds: float, now: Optional[datetime] = None) -> bool:
        current = now or datetime.now(timezone.utc)
        probed = datetime.fromisoformat(self.probed_at)
        if probed.tzinfo is None:
            probed = probed.replace(tzinfo=timezone.utc)
        return (current - probed).total_seconds() <= max_age_seconds


@dataclass(frozen=True)
class CloudNativeConnectivityReference:
    """A reference to an already-provisioned provider-native private-connectivity
    mechanism. AKAAL consumes this; it never provisions the underlying cloud fabric."""
    mechanism: CloudNativeConnectivityMechanism
    native_resource_ref: str
    proof_state: ConnectivityProofState = ConnectivityProofState.CONFIGURED

    def __post_init__(self) -> None:
        if not self.native_resource_ref or not self.native_resource_ref.strip():
            raise ConnectivityValidationError("CloudNativeConnectivityReference.native_resource_ref must be non-empty.")


@dataclass(frozen=True)
class ConnectivityEdge:
    """
    Immutable declaration of a connectivity path between a source and destination
    location (environment_id or execution site_id references -- this module does not
    care which, it only carries opaque string refs so it never re-derives environment/
    site validation logic that belongs to those packages).
    """
    edge_id: str
    source_ref: str
    destination_ref: str
    connectivity_class: ConnectivityClass
    is_private: bool
    encryption_required: bool = True
    authentication_required: bool = True
    requires_proxy: bool = False
    requires_bastion: bool = False
    requires_tunnel: bool = False
    cloud_native_reference: Optional[CloudNativeConnectivityReference] = None
    proof_state: ConnectivityProofState = ConnectivityProofState.CONFIGURED
    last_evidence: Optional[ReachabilityEvidence] = None
    policy_attributes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    topology_provenance: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not self.edge_id or not self.edge_id.strip():
            raise ConnectivityValidationError("ConnectivityEdge.edge_id must be non-empty.")
        if not self.source_ref or not self.destination_ref:
            raise ConnectivityValidationError("ConnectivityEdge requires non-empty source_ref and destination_ref.")
        if self.source_ref == self.destination_ref:
            raise ConnectivityValidationError("ConnectivityEdge source_ref and destination_ref must differ (no self-loop hop).")
        if not isinstance(self.policy_attributes, MappingProxyType):
            object.__setattr__(self, "policy_attributes", MappingProxyType(dict(self.policy_attributes)))

    def is_proven(self) -> bool:
        """CONFIGURED alone is never truthfully reachable -- only a live PROVEN state counts."""
        return self.proof_state == ConnectivityProofState.PROVEN

    def elevate_to_proven(self, evidence: ReachabilityEvidence) -> "ConnectivityEdge":
        """
        Returns a NEW edge reflecting the outcome of a real reachability probe.
        Configuration alone can never do this -- evidence is mandatory, and (Round-2
        hardening) it must genuinely apply to THIS edge and THIS edge's privacy
        requirement:
          * evidence produced for a different edge (`bound_edge_id` mismatch) is refused
            outright -- it can never be replayed onto this edge, even if it reports
            succeeded=True.
          * for an `is_private` edge, a successful-but-only-PUBLIC/TLS probe result is
            refused outright rather than silently accepted as proof of a private path --
            "public path used to prove private path" is exactly the attack this rejects.
        """
        if evidence.bound_edge_id != self.edge_id:
            raise ConnectivityValidationError(
                f"ReachabilityEvidence is bound to edge {evidence.bound_edge_id!r}, not "
                f"this edge {self.edge_id!r}; refusing to accept evidence produced for a "
                f"different edge/route/endpoint."
            )
        if self.is_private and evidence.succeeded and _PRIVACY_RANK[evidence.achieved_privacy] < _PRIVACY_RANK[PrivacyAchieved.PRIVATE]:
            raise ConnectivityValidationError(
                f"Edge {self.edge_id!r} requires private connectivity, but the supplied "
                f"evidence only achieved {evidence.achieved_privacy.value!r} privacy; "
                f"refusing to treat a public/TLS-only probe as proof of a private path."
            )
        new_state = ConnectivityProofState.PROVEN if evidence.succeeded else ConnectivityProofState.PROVEN_FAILED
        return ConnectivityEdge(
            edge_id=self.edge_id,
            source_ref=self.source_ref,
            destination_ref=self.destination_ref,
            connectivity_class=self.connectivity_class,
            is_private=self.is_private,
            encryption_required=self.encryption_required,
            authentication_required=self.authentication_required,
            requires_proxy=self.requires_proxy,
            requires_bastion=self.requires_bastion,
            requires_tunnel=self.requires_tunnel,
            cloud_native_reference=self.cloud_native_reference,
            proof_state=new_state,
            last_evidence=evidence,
            policy_attributes=self.policy_attributes,
            topology_provenance=self.topology_provenance,
        )

    def mark_stale(self) -> "ConnectivityEdge":
        """Explicit staleness transition -- proof does not last forever; callers (e.g. a
        periodic reachability sweep) must actively re-probe rather than trust old PROVEN
        state indefinitely."""
        if self.proof_state != ConnectivityProofState.PROVEN:
            return self
        return ConnectivityEdge(
            edge_id=self.edge_id,
            source_ref=self.source_ref,
            destination_ref=self.destination_ref,
            connectivity_class=self.connectivity_class,
            is_private=self.is_private,
            encryption_required=self.encryption_required,
            authentication_required=self.authentication_required,
            requires_proxy=self.requires_proxy,
            requires_bastion=self.requires_bastion,
            requires_tunnel=self.requires_tunnel,
            cloud_native_reference=self.cloud_native_reference,
            proof_state=ConnectivityProofState.PROVEN_STALE,
            last_evidence=self.last_evidence,
            policy_attributes=self.policy_attributes,
            topology_provenance=self.topology_provenance,
        )
