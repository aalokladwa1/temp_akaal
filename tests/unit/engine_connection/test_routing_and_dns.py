"""
Unit tests for akaalEngine.connection.routing
=============================================
Verifies DNS Happy Eyeballs resolution, timing, caching, and route coordinator.
"""

from akaalEngine.connection.models.endpoint import EndpointSpec, RouteSpec, RouteType
from akaalEngine.connection.routing.dns import EnterpriseDNSResolver
from akaalEngine.connection.routing.resolver import RouteResolver


def test_dns_resolver_localhost():
    resolver = EnterpriseDNSResolver()
    res = resolver.resolve("localhost")
    assert res.hostname == "localhost"
    assert res.primary_ip == "127.0.0.1"
    assert res.dns_time_ms >= 0.0
    assert not res.is_expired()


def test_dns_resolver_ip_literal():
    resolver = EnterpriseDNSResolver()
    res = resolver.resolve("192.168.1.50")
    assert res.primary_ip == "192.168.1.50"
    assert res.dns_time_ms == 0.0


def test_route_resolver_direct():
    route_resolver = RouteResolver()
    spec = EndpointSpec(
        provider_id="postgresql",
        host="localhost",
        port=5432,
        route_spec=RouteSpec(route_type=RouteType.DIRECT),
    )
    resolved = route_resolver.resolve_route(spec)
    assert resolved.effective_host == "localhost"
    assert resolved.effective_port == 5432
    assert resolved.route_type == RouteType.DIRECT
    assert resolved.tunnel_lease is None


def test_route_resolver_private_endpoint():
    route_resolver = RouteResolver()
    spec = EndpointSpec(
        provider_id="postgresql",
        host="vpce-12345.rds.amazonaws.com",
        port=5432,
        route_spec=RouteSpec(
            route_type=RouteType.PRIVATE_ENDPOINT,
            private_endpoint_id="vpce-12345",
        ),
    )
    resolved = route_resolver.resolve_route(spec)
    assert resolved.route_type == RouteType.PRIVATE_ENDPOINT
    assert resolved.effective_port == 5432
