"""
akaalEngine.discovery.strategies.nosql.cosmosdb
=================================================
Canonical Azure Cosmos DB discovery strategy (P7A Campaign B, provider #44).
Introspects container/partition-key metadata via the real azure-cosmos SDK
(`database.list_containers()`, `container.read()`) and performs bounded item sampling
for polymorphic document-shape inference -- Cosmos enforces no schema outside the
partition key, so structure facts are truthfully partial, never a fabricated complete
relational schema.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.sampling import InferredDocumentShape, SampledRecordSet
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts, PrimaryKeyFacts
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.nosql import NoSQLDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.cosmosdb")


class CosmosDBDiscoveryStrategy(NoSQLDiscoveryStrategy):
    """Azure Cosmos DB physical discovery strategy -- distributed multi-model store."""

    PROVIDER_ID = "cosmosdb"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(self, connection: Any, spec: EndpointSpec, route: Optional[ResolvedRoute] = None) -> DiscoveredEndpointIdentity:
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID, vendor_name="Microsoft Azure", engine_name="Azure Cosmos DB", system_type="COSMOSDB",
            version=ServerVersion(raw_version_string="Cosmos DB (managed service, no client-visible version)", major=0, minor=0, patch=0),
            edition=EngineEdition(edition_name="Managed Service", is_enterprise=False),
            host=spec.host or "cosmos.azure.com", port=443, database_name=spec.database_name,
        )

    def discover_namespaces(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> NamespaceInventory:
        db_name = spec.database_name or spec.options.get("database") or ""
        return NamespaceInventory(schemas=(db_name,) if db_name else (), default_schema=db_name or None)

    def discover_objects_page(self, connection: Any, spec: EndpointSpec, schema_name: str, context: DiscoveryContext, cursor: Optional[str] = None, page_size: int = 500) -> ObjectInventoryPage:
        items = []
        # `connection` is a Database or ContainerProxy depending on how deep the endpoint
        # options resolved -- list_containers() only exists on a Database-level handle.
        if connection is not None and hasattr(connection, "list_containers"):
            try:
                for props in connection.list_containers():
                    items.append(TableFacts(name=props.get("id", ""), schema_name=schema_name, object_type=ObjectType.COLLECTION, classification=ObjectClassification.USER))
            except Exception as exc:
                logger.warning(f"Error listing Cosmos DB containers: {exc}")
                raise
        return ObjectInventoryPage(items=tuple(items), cursor=None, is_last_page=True)

    def discover_object_structure(self, connection: Any, spec: EndpointSpec, schema_name: str, object_name: str, context: DiscoveryContext) -> ObjectStructureFacts:
        cols, primary_key = [], None
        container = connection
        if connection is not None and hasattr(connection, "get_container_client"):
            container = connection.get_container_client(object_name)
        if container is not None and hasattr(container, "read"):
            try:
                props = container.read()
                pk_paths = (props.get("partitionKey", {}) or {}).get("paths", [])
                pk_cols = [p.lstrip("/") for p in pk_paths]
                for i, c in enumerate(pk_cols):
                    cols.append(ColumnPhysicalMetadata(name=c, ordinal_position=i + 1, native_type="STRING", nullable=False, is_identity=True))
                if pk_cols:
                    primary_key = PrimaryKeyFacts(name=f"{object_name}_pk", table_name=object_name, columns=tuple(pk_cols), schema_name=schema_name)
            except Exception as exc:
                logger.warning(f"Error reading Cosmos DB container properties for {object_name}: {exc}")
                raise
        return ObjectStructureFacts(table_name=object_name, schema_name=schema_name, columns=tuple(cols), primary_key=primary_key)

    def infer_document_shape(self, connection: Any, spec: EndpointSpec, schema_name: str, collection_name: str, sample_size: int = 100) -> InferredDocumentShape:
        docs = []
        container = connection
        if connection is not None and hasattr(connection, "get_container_client"):
            container = connection.get_container_client(collection_name)
        if container is not None and hasattr(container, "query_items"):
            try:
                for item in container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True, max_item_count=min(sample_size, 100)):
                    docs.append(item)
                    if len(docs) >= sample_size:
                        break
            except Exception as exc:
                logger.warning(f"Error sampling Cosmos DB items for shape inference: {exc}")
        return DeterministicSampler.infer_shape_from_documents(collection_name, schema_name, docs)

    def check_read_only_permissions(self, connection: Any, spec: EndpointSpec) -> ThreeStatePermission:
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "read"):
            try:
                connection.read()
                cat_perm = ThreeStatePermission.PROVEN
            except Exception:
                cat_perm = ThreeStatePermission.DENIED
        return PermissionAssessment(read_only_verified=ThreeStatePermission.UNKNOWN, metadata_catalog_read=cat_perm)

    def discover_environment(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> ConfigurationFacts:
        return ConfigurationFacts(charset=CharsetFacts(server_encoding="UTF-8"), timezone=TimezoneFacts(database_timezone="UTC"), limits=LimitsFacts(max_connections=None))

    def discover_topology(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> TopologySnapshot:
        node = ClusterNodeFacts(node_id="cosmosdb-managed-endpoint", host=spec.host or "cosmos.azure.com", port=443, role=NodeRole.UNKNOWN)
        return TopologySnapshot(is_clustered=True, connected_node_role=NodeRole.UNKNOWN, nodes=(node,))

    def discover_cdc_prerequisites(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> CDCPrerequisiteSnapshot:
        return CDCPrerequisiteSnapshot(is_cdc_ready=False, mechanism=CDCMechanism.UNSUPPORTED, blocker_reasons=("No Cosmos DB Change Feed capture module implemented in this Engine.",))

    def sample_data(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, limit: int = 100, timeout_seconds: float = 3.0) -> SampledRecordSet:
        container = connection
        if connection is not None and hasattr(connection, "get_container_client"):
            container = connection.get_container_client(table_name)
        if container is None or not hasattr(container, "query_items"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            rows = []
            for item in container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True, max_item_count=min(limit, 100)):
                rows.append(item)
                if len(rows) >= limit:
                    break
            cols = sorted({k for row in rows for k in row.keys()})
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling Cosmos DB container {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

    def get_schema_change_marker(self, connection: Any, spec: EndpointSpec) -> Optional[str]:
        return None
