"""
akaalEngine.discovery.strategies.nosql.keydb
============================================
Canonical KeyDB multithreaded caching discovery strategy.
Extends Redis discovery strategy with KeyDB-specific architecture and version detection.
"""

from __future__ import annotations

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.strategies.nosql.redis import RedisDiscoveryStrategy


class KeyDBDiscoveryStrategy(RedisDiscoveryStrategy):
    """KeyDB multithreaded in-memory store physical discovery strategy."""

    PROVIDER_ID = "keydb"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        base_id = super().discover_endpoint_identity(connection, spec, route)
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Snap Inc. / KeyDB",
            engine_name="KeyDB Multithreaded Store",
            system_type="KEYDB",
            version=base_id.version,
            edition=EngineEdition(edition_name="KeyDB Enterprise", is_enterprise=False),
            host=spec.host,
            port=spec.port or 6379,
            database_name=str(spec.options.get("db", 0)),
        )
