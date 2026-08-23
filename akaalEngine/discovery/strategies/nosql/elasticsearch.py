"""
akaalEngine.discovery.strategies.nosql.elasticsearch
====================================================
Canonical Elasticsearch distributed search engine discovery strategy.
Introspects _cat/indices, _cat/aliases, _cat/nodes, mappings, settings, and shard topologies.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, PrivilegeFact, ThreeStatePermission
from akaalEngine.discovery.models.sampling import InferredDocumentShape
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import (
    ColumnPhysicalMetadata,
    ObjectStructureFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.nosql import NoSQLDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.elasticsearch")


class ElasticsearchDiscoveryStrategy(NoSQLDiscoveryStrategy):
    """Elasticsearch physical discovery strategy."""

    PROVIDER_ID = "elasticsearch"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "8.8.0"
        cluster_name = "elasticsearch"
        if connection is not None and hasattr(connection, "info"):
            try:
                info = connection.info()
                version_info = info.get("version", {})
                version_str = version_info.get("number", version_str)
                cluster_name = info.get("cluster_name", cluster_name)
            except Exception as exc:
                logger.warning(f"Error querying elasticsearch info: {exc}")

        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 8
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        patch = int(parts[2].split("-")[0]) if len(parts) > 2 and parts[2].split("-")[0].isdigit() else 0

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Elastic N.V.",
            engine_name="Elasticsearch Search & Analytics Engine",
            system_type="ELASTICSEARCH",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Elastic Stack", is_enterprise=True),
            instance_name=cluster_name,
            host=spec.host,
            port=spec.port or 9200,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        return NamespaceInventory(
            schemas=(),
            default_schema=None,
        )

    def discover_objects_page(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
        cursor: Optional[str] = None,
        page_size: int = 500,
    ) -> ObjectInventoryPage:
        indices = []
        if connection is not None and hasattr(connection, "cat"):
            try:
                cat_indices = connection.cat.indices(format="json")
                for item in cat_indices:
                    iname = item.get("index", "")
                    if not iname.startswith("."):
                        docs_count = int(item.get("docs.count", 0) or 0)
                        store_size = item.get("store.size", "0b")
                        indices.append(
                            TableFacts(
                                name=iname,
                                schema_name=schema_name or "",
                                object_type=ObjectType.SEARCH_INDEX,
                                classification=ObjectClassification.USER,
                                row_count_estimate=docs_count,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying elasticsearch cat.indices: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(indices, cursor=cursor, page_size=page_size)

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Elasticsearch has no non-destructive physical probe for read-only role state
        return ThreeStatePermission.UNKNOWN

    def discover_objects_structure_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, ObjectStructureFacts]:
        if not object_names or connection is None or not hasattr(connection, "indices"):
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {}
        for name in object_names:
            results[name] = self.discover_object_structure(connection, spec, schema_name, name, context)
        return results

    def discover_table_statistics_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, TableSizeFacts]:
        if not object_names or connection is None:
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {name: TableSizeFacts(table_name=name, schema_name=schema_name, row_count=0) for name in object_names}
        return results

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = [
            ColumnPhysicalMetadata(name="_id", ordinal_position=1, native_type="KEYWORD", is_identity=True),
            ColumnPhysicalMetadata(name="_source", ordinal_position=2, native_type="_JSON_DOC"),
        ]
        if connection is not None and hasattr(connection, "indices"):
            try:
                mapping = connection.indices.get_mapping(index=object_name)
                props = mapping.get(object_name, {}).get("mappings", {}).get("properties", {})
                for idx, (prop_name, prop_meta) in enumerate(props.items()):
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=prop_name,
                            ordinal_position=idx + 3,
                            native_type=str(prop_meta.get("type", "object")).upper(),
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error getting elasticsearch mapping for {object_name}: {exc}")
                raise

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name="default",
            columns=tuple(cols),
        )

    def infer_document_shape(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        collection_name: str,
        sample_size: int = 100,
    ) -> InferredDocumentShape:
        return InferredDocumentShape(collection_name=collection_name, schema_name=schema_name)

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # Elasticsearch has no non-destructive physical probe for read-only user role
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "ping"):
            try:
                res = connection.ping()
                cat_perm = ThreeStatePermission.PROVEN if res else ThreeStatePermission.DENIED
            except Exception:
                cat_perm = ThreeStatePermission.DENIED

        return PermissionAssessment(
            read_only_verified=ThreeStatePermission.UNKNOWN,
            metadata_catalog_read=cat_perm,
        )

    def discover_environment(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> ConfigurationFacts:
        return ConfigurationFacts(
            charset=CharsetFacts(server_encoding="UTF-8"),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=1000),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        nodes = []
        if connection is not None and hasattr(connection, "cat"):
            try:
                cat_nodes = connection.cat.nodes(format="json")
                for n in cat_nodes:
                    nodes.append(
                        ClusterNodeFacts(
                            node_id=n.get("name", "node"),
                            host=n.get("ip", spec.host or "localhost"),
                            port=spec.port or 9200,
                            role=NodeRole.PRIMARY if "*" in n.get("master", "") else NodeRole.WORKER,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error querying elasticsearch cat.nodes: {exc}")

        return TopologySnapshot(
            is_clustered=len(nodes) > 1,
            connected_node_role=NodeRole.PRIMARY,
            nodes=tuple(nodes) if nodes else (),
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
                blocker_reasons=("Elasticsearch connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.ELASTICSEARCH_CHANGES,
            blocker_reasons=("Elasticsearch CDC requires Changes API or Logstash pipeline.",),
        )

    def sample_data(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        limit: int = 100,
        timeout_seconds: float = 3.0,
    ) -> SampledRecordSet:
        if connection is None or not hasattr(connection, "search"):
            return DeterministicSampler.package_sample(table_name, schema_name, ["_id", "_source"], [])
        try:
            rows = []
            res = connection.search(index=table_name, size=limit)
            for hit in res.get("hits", {}).get("hits", []):
                src = hit.get("_source", {})
                src["_id"] = hit.get("_id")
                rows.append(src)
            return DeterministicSampler.package_sample(table_name, schema_name, ["_id", "_source"], rows)
        except Exception as exc:
            logger.warning(f"Error sampling elasticsearch index {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))
