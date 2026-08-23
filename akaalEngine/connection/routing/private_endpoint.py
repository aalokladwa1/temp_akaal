"""
akaalEngine.connection.routing.private_endpoint
===============================================
Private endpoint, AWS PrivateLink, Azure Private Link, and GCP PSC route resolution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from akaalEngine.connection.models.endpoint import RouteSpec, RouteType
from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    RouteResolutionError,
)
from akaalEngine.connection.security.redaction import SafeReprMixin

logger = logging.getLogger("akaalEngine.connection.routing.private_endpoint")


@dataclass(frozen=True)
class PrivateEndpointResolution(SafeReprMixin):
    """Result of resolving a private link or VPC endpoint."""
    endpoint_id: str
    target_host: str
    target_port: int
    is_active: bool
    private_ip: Optional[str] = None
    dns_zone: Optional[str] = None
    details: Mapping[str, Any] = field(default_factory=dict)


class PrivateEndpointResolver:
    """Resolves cloud private endpoint bindings into physical network targets."""

    @classmethod
    def resolve_private_route(
        cls,
        route_spec: RouteSpec,
        host: str,
        port: int,
    ) -> PrivateEndpointResolution:
        if route_spec.route_type != RouteType.PRIVATE_ENDPOINT or not route_spec.private_endpoint_id:
            return PrivateEndpointResolution(
                endpoint_id="none",
                target_host=host,
                target_port=port,
                is_active=True,
            )

        pe_id = route_spec.private_endpoint_id
        logger.info(f"[PrivateEndpointResolver] Resolving private endpoint '{pe_id}' for {host}:{port}")

        # In standard VPC environments, private endpoint ID maps to private DNS or host alias
        return PrivateEndpointResolution(
            endpoint_id=pe_id,
            target_host=host,
            target_port=port,
            is_active=True,
            details={"configured_private_endpoint_id": pe_id},
        )
