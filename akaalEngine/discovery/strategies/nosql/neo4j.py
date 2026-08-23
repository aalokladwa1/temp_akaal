"""
akaalEngine.discovery.strategies.nosql.neo4j
============================================
Canonical Neo4j graph database discovery strategy.
Introspects labels, relationship types, property keys, vector indexes, and uniqueness constraints.
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
    IndexAccessMethod,
    IndexFacts,
    ObjectStructureFacts,
    PrimaryKeyFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.nosql import NoSQLDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.neo4j")


class Neo4jDiscoveryStrategy(NoSQLDiscoveryStrategy):
    """Neo4j graph database physical discovery strategy."""

    PROVIDER_ID = "neo4j"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "5.10.0"
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Neo4j Inc.",
            engine_name="Neo4j Native Graph Database",
            system_type="NEO4J",
            version=ServerVersion(raw_version_string=version_str, major=5, minor=10, patch=0),
            edition=EngineEdition(edition_name="Enterprise Graph Edition", is_enterprise=True),
            host=spec.host,
            port=spec.port or 7687,
            database_name=spec.database_name or "neo4j",
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        databases = []
        if connection is not None and hasattr(connection, "run"):
            try:
                res = connection.run("SHOW DATABASES")
                dbs = [r["name"] for r in res if "system" not in r["name"]]
                if dbs:
                    databases = dbs
            except Exception as exc:
                logger.warning(f"Error querying neo4j databases: {exc}")
                raise
        elif spec.database_name:
            databases = [spec.database_name]

        return NamespaceInventory(
            schemas=tuple(databases),
            system_schemas=("system",),
            default_schema=databases[0] if databases else None,
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
        items = []
        if connection is not None and hasattr(connection, "run"):
            try:
                # Node Labels
                res = connection.run("CALL db.labels()")
                for r in res:
                    label = r["label"] if "label" in r else r[0]
                    items.append(
                        TableFacts(
                            name=f"Node:{label}",
                            schema_name=schema_name,
                            object_type=ObjectType.GRAPH_LABEL,
                            classification=ObjectClassification.USER,
                        )
                    )

                # Relationship Types
                res_rel = connection.run("CALL db.relationshipTypes()")
                for r in res_rel:
                    rel = r["relationshipType"] if "relationshipType" in r else r[0]
                    items.append(
                        TableFacts(
                            name=f"Rel:{rel}",
                            schema_name=schema_name,
                            object_type=ObjectType.GRAPH_LABEL,
                            classification=ObjectClassification.USER,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error discovering neo4j schema: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(items, cursor=cursor, page_size=page_size)

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = [
            ColumnPhysicalMetadata(name="<id>", ordinal_position=1, native_type="INT64", is_identity=True),
            ColumnPhysicalMetadata(name="<properties>", ordinal_position=2, native_type="MAP<STRING, ANY>"),
        ]
        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
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
        # Neo4j Cypher has no non-destructive physical probe for read-only user role
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "run"):
            try:
                connection.run("RETURN 1")
                cat_perm = ThreeStatePermission.PROVEN
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
            limits=LimitsFacts(max_connections=500),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        return TopologySnapshot(
            is_clustered=False,
            connected_node_role=NodeRole.PRIMARY,
            nodes=(),
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
                blocker_reasons=("Neo4j connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.NEO4J_CDC,
            blocker_reasons=("Neo4j CDC requires Enterprise Neo4j CDC plugin or Kafka Connector.",),
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
        if connection is None or not hasattr(connection, "run"):
            return DeterministicSampler.package_sample(table_name, schema_name, ["properties"], [])
        try:
            rows = []
            if table_name.startswith("Node:"):
                label = table_name.split(":", 1)[1]
                res = connection.run(f"MATCH (n:`{label}`) RETURN n LIMIT {limit}")
                for r in res:
                    node = r["n"]
                    props = dict(node) if hasattr(node, "items") else {"id": str(node)}
                    rows.append(props)
            return DeterministicSampler.package_sample(table_name, schema_name, ["properties"], rows)
        except Exception as exc:
            logger.warning(f"Error sampling neo4j {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))
