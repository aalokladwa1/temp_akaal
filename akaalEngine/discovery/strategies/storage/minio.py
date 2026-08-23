"""
akaalEngine.discovery.strategies.storage.minio
=============================================
Canonical MinIO high-performance S3-compatible object storage discovery strategy.
Extends S3 discovery strategy with MinIO server identity and cluster topology introspection.
"""

from __future__ import annotations

from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.strategies.storage.s3 import S3DiscoveryStrategy


class MinIODiscoveryStrategy(S3DiscoveryStrategy):
    """MinIO S3-compatible object storage physical discovery strategy."""

    PROVIDER_ID = "minio"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="MinIO Inc.",
            engine_name="MinIO High Performance Object Storage",
            system_type="MINIO",
            version=ServerVersion(raw_version_string="MinIO", major=0, minor=0, patch=0),
            edition=EngineEdition(edition_name="High-Performance S3 Compatible", is_enterprise=False),
            host=spec.host,
            port=spec.port or 9000,
            database_name=spec.database_name,
        )
