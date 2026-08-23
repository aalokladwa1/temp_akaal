"""
akaalEngine.discovery.strategies.nosql.opensearch
================================================
Canonical OpenSearch distributed search discovery strategy.
Extends Elasticsearch discovery strategy for OpenSearch-specific vector engines and index properties.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.strategies.nosql.elasticsearch import ElasticsearchDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.opensearch")


class OpenSearchDiscoveryStrategy(ElasticsearchDiscoveryStrategy):
    """OpenSearch physical discovery strategy."""

    PROVIDER_ID = "opensearch"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "2.8.0"
        cluster_name = "opensearch-cluster"
        if connection is not None and hasattr(connection, "info"):
            try:
                info = connection.info()
                version_info = info.get("version", {})
                version_str = version_info.get("number", version_str)
                cluster_name = info.get("cluster_name", cluster_name)
            except Exception:
                pass

        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 2
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 8
        patch = int(parts[2].split("-")[0]) if len(parts) > 2 and parts[2].split("-")[0].isdigit() else 0

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="OpenSearch Project / AWS",
            engine_name="OpenSearch Distributed Engine",
            system_type="OPENSEARCH",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="OpenSearch Community / Managed", is_enterprise=True),
            instance_name=cluster_name,
            host=spec.host,
            port=spec.port or 9200,
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
                blocker_reasons=("OpenSearch connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.OPENSEARCH_CHANGES,
            blocker_reasons=("OpenSearch CDC requires Changes API or Logstash pipeline.",),
        )

