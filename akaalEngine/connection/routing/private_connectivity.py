"""akaalEngine.connection.routing.private_connectivity
====================================================
P7.9 Truthful private-connectivity capability declaration.

AKAAL can CONSUME an already-provisioned private network path (a private endpoint /
PrivateLink / VNet-peering attachment the operator's cloud environment already exposes)
by routing through it via RouteSpec.private_endpoint_id. AKAAL does NOT provision cloud
private-network fabric itself -- creating VPC peering, PrivateLink endpoints, or VNet
attachments is cloud infrastructure orchestration reserved for the future P7B Cloud +
Hybrid + Data Fabric platform, not this module.

This module exists so that capability truth is explicit and machine-checkable rather
than silently assumed: callers must not claim private connectivity is available unless
this declares SUPPORTED, and must not interpret UNSUPPORTED as "will provision it".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from akaalEngine.connection.models.endpoint import RouteSpec, RouteType


class PrivateConnectivityMode(str, Enum):
    CONSUME_EXISTING = "CONSUME_EXISTING"            # a private endpoint is already provisioned and referenced
    PROVISIONING_UNSUPPORTED = "PROVISIONING_UNSUPPORTED"  # AKAAL does not create private network fabric (P7B scope)


@dataclass(frozen=True)
class PrivateConnectivityCapability:
    supported: bool
    mode: PrivateConnectivityMode
    detail: str


def declare_private_connectivity_capability(route_spec: RouteSpec) -> PrivateConnectivityCapability:
    """
    Truthfully reports whether the supplied RouteSpec can actually be routed over a
    private path in this environment. Never claims capability it cannot deliver.
    """
    if route_spec.route_type == RouteType.PRIVATE_ENDPOINT and route_spec.private_endpoint_id:
        return PrivateConnectivityCapability(
            supported=True,
            mode=PrivateConnectivityMode.CONSUME_EXISTING,
            detail=(
                f"Routing will consume pre-provisioned private endpoint "
                f"{route_spec.private_endpoint_id!r}. AKAAL does not create or manage the "
                f"underlying private network attachment."
            ),
        )

    return PrivateConnectivityCapability(
        supported=False,
        mode=PrivateConnectivityMode.PROVISIONING_UNSUPPORTED,
        detail=(
            "No pre-provisioned private_endpoint_id was supplied. AKAAL cannot provision "
            "cloud private-network fabric (VPC peering / PrivateLink / VNet attachment) -- "
            "that capability is out of scope for P7.9 and is reserved for the future P7B "
            "Cloud + Hybrid + Data Fabric platform. Provide an operator-provisioned "
            "private_endpoint_id to route over a private path, or accept a non-private route."
        ),
    )
