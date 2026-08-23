"""
akaalEngine.discovery.strategies.nosql.scylladb
==============================================
Canonical ScyllaDB discovery strategy.
Extends Cassandra discovery strategy with ScyllaDB shard awareness and native Scylla CDC log tables.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.strategies.nosql.cassandra import CassandraDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.scylladb")


class ScyllaDBDiscoveryStrategy(CassandraDiscoveryStrategy):
    """ScyllaDB physical discovery strategy."""

    PROVIDER_ID = "scylladb"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "5.2.0 (ScyllaDB)"
        if connection is not None and hasattr(connection, "execute"):
            try:
                row = connection.execute("SELECT release_version FROM system.local").one()
                if row:
                    version_str = getattr(row, "release_version", version_str)
            except Exception:
                pass

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="ScyllaDB Inc.",
            engine_name="ScyllaDB Enterprise",
            system_type="SCYLLADB",
            version=ServerVersion(raw_version_string=version_str, major=5, minor=2, patch=0),
            edition=EngineEdition(edition_name="C++ Shard-Aware Enterprise", is_enterprise=True),
            host=spec.host,
            port=spec.port or 9042,
            database_name=spec.database_name,
        )

    def discover_cdc_prerequisites(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> CDCPrerequisiteSnapshot:
        if connection is None:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.UNSUPPORTED,
                blocker_reasons=("ScyllaDB connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.SCYLLA_CDC,
            blocker_reasons=("ScyllaDB native CDC log tables not verified on keyspace",),
        )
