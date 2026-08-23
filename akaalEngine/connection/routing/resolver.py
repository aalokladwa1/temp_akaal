"""
akaalEngine.connection.routing.resolver
======================================
Comprehensive route resolution coordinator.
Binds DNS resolution, PrivateLink endpoints, Proxies, and SSH Bastions to feed physical provider connection configs.
Guarantees that every physical endpoint in single and clustered configurations participates in canonical routing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec, RouteSpec, RouteType
from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    RouteResolutionError,
)
from akaalEngine.connection.routing.dns import EnterpriseDNSResolver, default_dns_resolver
from akaalEngine.connection.routing.private_endpoint import PrivateEndpointResolver
from akaalEngine.connection.routing.proxy import ProxyTunnel, ProxyTunnelLease
from akaalEngine.connection.routing.ssh import SSHTunnelLease, SSHTunnelRuntime
from akaalEngine.connection.security.redaction import SafeReprMixin
from akaalEngine.connection.security.secret_consumer import SecretConsumer, default_secret_consumer

logger = logging.getLogger("akaalEngine.connection.routing.resolver")


def _parse_endpoint_address(raw: str, default_port: int = 0) -> Tuple[str, int, Optional[str]]:
    """Parses host, port, and optional scheme from an endpoint address string."""
    raw = raw.strip()
    scheme = None
    if "://" in raw:
        scheme, raw = raw.split("://", 1)

    host = raw
    port = default_port

    if raw.startswith("["):
        # IPv6 [addr]:port or [addr]
        if "]" in raw:
            end_bracket = raw.index("]")
            host = raw[1:end_bracket]
            rest = raw[end_bracket + 1 :]
            if rest.startswith(":"):
                try:
                    port = int(rest[1:])
                except ValueError:
                    port = default_port
    elif ":" in raw:
        parts = raw.rsplit(":", 1)
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            port = default_port

    return host, port, scheme


@dataclass(frozen=True)
class ResolvedEndpointTarget(SafeReprMixin):
    """
    Represents a single canonically routed physical endpoint target.
    """
    effective_host: str
    effective_port: int
    resolved_ip: Optional[str] = None
    dns_time_ms: float = 0.0
    scheme: Optional[str] = None
    raw_endpoint: Optional[str] = None

    def format_address(self, include_scheme: bool = False) -> str:
        """Formats the target into host:port or scheme://host:port string."""
        prefix = f"{self.scheme}://" if include_scheme and self.scheme else ""
        if ":" in self.effective_host and not self.effective_host.startswith("["):
            # IPv6
            return f"{prefix}[{self.effective_host}]:{self.effective_port}"
        if self.effective_port > 0:
            return f"{prefix}{self.effective_host}:{self.effective_port}"
        return f"{prefix}{self.effective_host}"


@dataclass
class ResolvedRoute(SafeReprMixin):
    """
    Physical network target ready to be passed directly to provider driver / client connection factories.
    Supports single target and multi-endpoint cluster configurations with full route governance.
    """
    effective_host: str
    effective_port: int
    resolved_ip: Optional[str] = None
    dns_time_ms: float = 0.0
    route_type: RouteType = RouteType.DIRECT
    tunnel_lease: Optional[Any] = None  # SSHTunnelLease or ProxyTunnelLease
    resolved_targets: Tuple[ResolvedEndpointTarget, ...] = field(default_factory=tuple)
    tunnel_leases: List[Any] = field(default_factory=list)
    _closed: bool = False

    def __post_init__(self) -> None:
        if not self.resolved_targets:
            primary = ResolvedEndpointTarget(
                effective_host=self.effective_host,
                effective_port=self.effective_port,
                resolved_ip=self.resolved_ip,
                dns_time_ms=self.dns_time_ms,
            )
            object.__setattr__(self, "resolved_targets", (primary,))
        if self.tunnel_lease and self.tunnel_lease not in self.tunnel_leases:
            self.tunnel_leases.append(self.tunnel_lease)

    def get_contact_points(self) -> List[str]:
        """Returns list of hosts/IPs for Cassandra / ScyllaDB contact points."""
        return [t.effective_host for t in self.resolved_targets]

    def get_bootstrap_servers(self) -> List[str]:
        """Returns list of host:port strings for Kafka bootstrap brokers or replica nodes."""
        return [t.format_address(include_scheme=False) for t in self.resolved_targets]

    def get_http_hosts(self) -> List[str]:
        """Returns list of URLs/hosts for Elasticsearch, OpenSearch, etc."""
        return [t.format_address(include_scheme=True) for t in self.resolved_targets]

    def close(self) -> None:
        """Cleans up active tunnel leases if established."""
        if not self._closed:
            self._closed = True
            for lease in self.tunnel_leases:
                try:
                    lease.close()
                except Exception:
                    pass
            if self.tunnel_lease and self.tunnel_lease not in self.tunnel_leases:
                try:
                    self.tunnel_lease.close()
                except Exception:
                    pass

    def __enter__(self) -> ResolvedRoute:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class RouteResolver:
    """
    Coordinates network route resolution for Connection Authority.
    Ensures that every endpoint (single or cluster) participates in canonical routing.
    """

    def __init__(
        self,
        dns_resolver: Optional[EnterpriseDNSResolver] = None,
        secret_consumer: Optional[SecretConsumer] = None,
    ) -> None:
        self.dns_resolver = dns_resolver or default_dns_resolver
        self.secret_consumer = secret_consumer or default_secret_consumer
        self.ssh_runtime = SSHTunnelRuntime(self.secret_consumer)
        self.proxy_tunnel = ProxyTunnel(self.secret_consumer)

    def resolve_route(self, spec: EndpointSpec) -> ResolvedRoute:
        """
        Resolves the EndpointSpec into an effective network route.
        Guarantees that every physical endpoint in spec.endpoints or (host, port)
        is canonically routed through DNS, PrivateLink, HTTP Proxy, or SSH Bastion.
        """
        route_spec = spec.route_spec
        provider_id = spec.provider_id.strip().lower()

        # Reject network routing on in-process providers like SQLite
        if provider_id == "sqlite" and route_spec.route_type != RouteType.DIRECT:
            msg = f"Provider '{provider_id}' is an in-process provider and does not support network route type '{route_spec.route_type.value}'."
            failure = ConnectionFailure(
                error_code="ROUTE_UNSUPPORTED_FOR_PROVIDER",
                category=FailureCategory.ROUTE_FAILURE,
                message=msg,
                retryable=False,
                provider_id=provider_id,
            )
            raise RouteResolutionError(failure)



        # Collect raw endpoint list to resolve
        raw_endpoints: List[str] = []
        default_port = spec.port or 0

        if spec.endpoints:
            raw_endpoints.extend(spec.endpoints)
        elif spec.host:
            raw_endpoints.append(f"{spec.host}:{default_port}" if default_port else spec.host)
        else:
            raw_endpoints.append(f"localhost:{default_port}")

        resolved_targets: List[ResolvedEndpointTarget] = []
        tunnel_leases: List[Any] = []
        total_dns_time_ms = 0.0

        for raw_ep in raw_endpoints:
            raw_host, raw_port, scheme = _parse_endpoint_address(raw_ep, default_port=default_port)
            if raw_port == 0 and default_port > 0:
                raw_port = default_port

            # 1. Private Endpoint Routing
            if route_spec.route_type == RouteType.PRIVATE_ENDPOINT:
                pe_res = PrivateEndpointResolver.resolve_private_route(route_spec, raw_host, raw_port)
                try:
                    dns_res = self.dns_resolver.resolve(pe_res.target_host)
                    resolved_ip = dns_res.primary_ip
                    dns_time_ms = dns_res.dns_time_ms
                except Exception:
                    resolved_ip = None
                    dns_time_ms = 0.0

                total_dns_time_ms += dns_time_ms
                resolved_targets.append(
                    ResolvedEndpointTarget(
                        effective_host=pe_res.target_host,
                        effective_port=pe_res.target_port,
                        resolved_ip=resolved_ip,
                        dns_time_ms=dns_time_ms,
                        scheme=scheme,
                        raw_endpoint=raw_ep,
                    )
                )
                continue

            # 2. DNS Resolution
            try:
                dns_res = self.dns_resolver.resolve(raw_host)
                resolved_ip = dns_res.primary_ip
                dns_time_ms = dns_res.dns_time_ms
            except Exception:
                resolved_ip = None
                dns_time_ms = 0.0

            total_dns_time_ms += dns_time_ms

            # 3. SSH Bastion Tunnel Routing
            if route_spec.route_type == RouteType.SSH_BASTION_TUNNEL:
                tunnel_lease = self.ssh_runtime.establish_tunnel(route_spec, raw_host, raw_port)
                tunnel_leases.append(tunnel_lease)
                resolved_targets.append(
                    ResolvedEndpointTarget(
                        effective_host=tunnel_lease.local_bind_host,
                        effective_port=tunnel_lease.local_bind_port,
                        resolved_ip="127.0.0.1",
                        dns_time_ms=dns_time_ms,
                        scheme=scheme,
                        raw_endpoint=raw_ep,
                    )
                )
                continue

            # 4. HTTP Proxy Routing (HTTP CONNECT)
            if route_spec.route_type == RouteType.HTTP_PROXY:
                proxy_lease = self.proxy_tunnel.establish_http_connect_tunnel(route_spec, raw_host, raw_port)
                tunnel_leases.append(proxy_lease)
                resolved_targets.append(
                    ResolvedEndpointTarget(
                        effective_host=proxy_lease.local_bind_host,
                        effective_port=proxy_lease.local_bind_port,
                        resolved_ip="127.0.0.1",
                        dns_time_ms=dns_time_ms,
                        scheme=scheme,
                        raw_endpoint=raw_ep,
                    )
                )
                continue

            # 4b. SOCKS5 Proxy Routing
            if route_spec.route_type == RouteType.SOCKS5_PROXY:
                proxy_lease = self.proxy_tunnel.establish_socks5_tunnel(route_spec, raw_host, raw_port)
                tunnel_leases.append(proxy_lease)
                resolved_targets.append(
                    ResolvedEndpointTarget(
                        effective_host=proxy_lease.local_bind_host,
                        effective_port=proxy_lease.local_bind_port,
                        resolved_ip="127.0.0.1",
                        dns_time_ms=dns_time_ms,
                        scheme=scheme,
                        raw_endpoint=raw_ep,
                    )
                )
                continue

            # 5. Direct / Happy Eyeballs
            resolved_targets.append(
                ResolvedEndpointTarget(
                    effective_host=raw_host,
                    effective_port=raw_port,
                    resolved_ip=resolved_ip,
                    dns_time_ms=dns_time_ms,
                    scheme=scheme,
                    raw_endpoint=raw_ep,
                )
            )

        primary_target = resolved_targets[0] if resolved_targets else ResolvedEndpointTarget("localhost", 0)
        primary_lease = tunnel_leases[0] if tunnel_leases else None

        return ResolvedRoute(
            effective_host=primary_target.effective_host,
            effective_port=primary_target.effective_port,
            resolved_ip=primary_target.resolved_ip,
            dns_time_ms=primary_target.dns_time_ms,
            route_type=route_spec.route_type,
            tunnel_lease=primary_lease,
            resolved_targets=tuple(resolved_targets),
            tunnel_leases=tunnel_leases,
        )


# Global default route resolver
default_route_resolver = RouteResolver()
