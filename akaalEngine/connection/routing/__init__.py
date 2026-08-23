"""
akaalEngine.connection.routing
==============================
DNS resolution, private endpoint routing, proxy tunneling, SSH bastion runtimes, and route resolver.
"""

from akaalEngine.connection.routing.dns import (
    DNSResolutionResult,
    EnterpriseDNSResolver,
    default_dns_resolver,
)

from akaalEngine.connection.routing.private_endpoint import (
    PrivateEndpointResolution,
    PrivateEndpointResolver,
)

from akaalEngine.connection.routing.proxy import (
    ProxyTunnel,
    ProxyTunnelLease,
)

from akaalEngine.connection.routing.ssh import (
    SSHTunnelLease,
    SSHTunnelRuntime,
)

from akaalEngine.connection.routing.resolver import (
    ResolvedRoute,
    RouteResolver,
    default_route_resolver,
)

__all__ = [
    "DNSResolutionResult",
    "EnterpriseDNSResolver",
    "default_dns_resolver",
    "PrivateEndpointResolution",
    "PrivateEndpointResolver",
    "ProxyTunnel",
    "ProxyTunnelLease",
    "SSHTunnelLease",
    "SSHTunnelRuntime",
    "ResolvedRoute",
    "RouteResolver",
    "default_route_resolver",
]
