"""
akaalEngine.discovery.strategies.nosql.dynamodb
====================================================
Canonical AWS DynamoDB discovery strategy (P7A Campaign B).

Introspects table inventory, key schema, GSI/LSI, per-table stream (CDC) status, and
performs bounded item sampling for document-shape inference. DynamoDB enforces schema
only for key attributes -- non-key attribute shape is genuinely polymorphic per item, so
structure/shape facts are truthfully partial, not fabricated as a complete relational
schema.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator, DiscoveryCursor
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.sampling import InferredDocumentShape, SampledRecordSet
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, IndexFacts, ObjectStructureFacts, PrimaryKeyFacts
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.nosql import NoSQLDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.dynamodb")


def _deserialize_item(item: dict) -> dict:
    try:
        from boto3.dynamodb.types import TypeDeserializer
        deser = TypeDeserializer()
        return {k: deser.deserialize(v) for k, v in item.items()}
    except Exception:
        return item


class DynamoDBDiscoveryStrategy(NoSQLDiscoveryStrategy):
    """AWS DynamoDB physical discovery strategy -- managed partition/sort-key store."""

    PROVIDER_ID = "dynamodb"

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
            vendor_name="Amazon Web Services",
            engine_name="AWS DynamoDB",
            system_type="DYNAMODB",
            version=ServerVersion(raw_version_string="DynamoDB (managed service, no client-visible version)", major=0, minor=0, patch=0),
            edition=EngineEdition(edition_name="Managed Service", is_enterprise=False),
            host=spec.host or "dynamodb.amazonaws.com",
            port=443,
            database_name=spec.options.get("table_name", ""),
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        # DynamoDB has no schema/database layer above tables -- all tables in the region
        # are the entire discoverable namespace.
        return NamespaceInventory(schemas=(), default_schema=None)

    def discover_objects_page(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
        cursor: Optional[str] = None,
        page_size: int = 500,
    ) -> ObjectInventoryPage:
        exclusive_start = None
        if cursor:
            try:
                dec = DiscoveryCursor.decode(cursor)
                exclusive_start = dec.provider_token
            except Exception:
                exclusive_start = None

        items = []
        next_cursor = None
        if connection is not None and hasattr(connection, "list_tables"):
            try:
                kwargs = {"Limit": min(page_size, 100)}
                if exclusive_start:
                    kwargs["ExclusiveStartTableName"] = exclusive_start
                resp = connection.list_tables(**kwargs)
                for tname in resp.get("TableNames", []):
                    items.append(
                        TableFacts(
                            name=tname,
                            schema_name=schema_name,
                            object_type=ObjectType.COLLECTION,
                            classification=ObjectClassification.USER,
                        )
                    )
                last_table = resp.get("LastEvaluatedTableName")
                if last_table:
                    next_cursor = DiscoveryCursor(schema_index=0, offset=0, provider_token=last_table).encode()
            except Exception as exc:
                logger.warning(f"Error listing DynamoDB tables: {exc}")
                raise

        return ObjectInventoryPage(
            items=tuple(items),
            cursor=next_cursor,
            is_last_page=next_cursor is None,
        )

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = []
        primary_key = None
        indexes = []

        if connection is not None and hasattr(connection, "describe_table"):
            try:
                desc = connection.describe_table(TableName=object_name).get("Table", {})
                attr_defs = {a["AttributeName"]: a["AttributeType"] for a in desc.get("AttributeDefinitions", [])}
                key_schema = desc.get("KeySchema", [])
                pk_cols = []
                for k in key_schema:
                    attr_name = k["AttributeName"]
                    is_hash = k["KeyType"] == "HASH"
                    pk_cols.append(attr_name)
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=attr_name,
                            ordinal_position=len(cols) + 1,
                            native_type=attr_defs.get(attr_name, "S"),
                            nullable=False,
                            is_identity=is_hash,
                        )
                    )
                if pk_cols:
                    primary_key = PrimaryKeyFacts(name=f"{object_name}_key", table_name=object_name, columns=tuple(pk_cols), schema_name=schema_name)

                for gsi in desc.get("GlobalSecondaryIndexes", []) or []:
                    idx_cols = tuple(k["AttributeName"] for k in gsi.get("KeySchema", []))
                    indexes.append(IndexFacts(name=gsi["IndexName"], table_name=object_name, schema_name=schema_name, columns=idx_cols, is_unique=False, is_primary=False))
                for lsi in desc.get("LocalSecondaryIndexes", []) or []:
                    idx_cols = tuple(k["AttributeName"] for k in lsi.get("KeySchema", []))
                    indexes.append(IndexFacts(name=lsi["IndexName"], table_name=object_name, schema_name=schema_name, columns=idx_cols, is_unique=False, is_primary=False))
            except Exception as exc:
                logger.warning(f"Error describing DynamoDB table {object_name}: {exc}")
                raise

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
            primary_key=primary_key,
            indexes=tuple(indexes),
        )

    def infer_document_shape(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        collection_name: str,
        sample_size: int = 100,
    ) -> InferredDocumentShape:
        docs = []
        if connection is not None and hasattr(connection, "scan"):
            try:
                resp = connection.scan(TableName=collection_name, Limit=min(sample_size, 100))
                for raw_item in resp.get("Items", []):
                    docs.append(_deserialize_item(raw_item))
            except Exception as exc:
                logger.warning(f"Error sampling DynamoDB items for shape inference: {exc}")

        return DeterministicSampler.infer_shape_from_documents(collection_name, schema_name, docs)

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "list_tables"):
            try:
                connection.list_tables(Limit=1)
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
            limits=LimitsFacts(max_connections=None),  # managed service, no client connection concept
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        # Fully managed: no client-visible node/partition topology.
        node = ClusterNodeFacts(
            node_id="dynamodb-managed-endpoint",
            host=spec.host or "dynamodb.amazonaws.com",
            port=443,
            role=NodeRole.UNKNOWN,
        )
        return TopologySnapshot(is_clustered=False, connected_node_role=NodeRole.UNKNOWN, nodes=(node,))

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
                blocker_reasons=("DynamoDB connection not established",),
            )

        table_name = spec.options.get("table_name")
        if not table_name:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.DYNAMODB_STREAMS,
                blocker_reasons=("No table_name specified in endpoint options; DynamoDB Streams status is per-table.",),
            )

        try:
            desc = connection.describe_table(TableName=table_name).get("Table", {})
            stream_spec = desc.get("StreamSpecification", {})
            enabled = bool(stream_spec.get("StreamEnabled"))
            blockers = () if enabled else (f"DynamoDB Streams not enabled on table '{table_name}'.",)
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=enabled,
                mechanism=CDCMechanism.DYNAMODB_STREAMS,
                blocker_reasons=blockers,
            )
        except Exception as exc:
            return CDCPrerequisiteSnapshot(
                is_cdc_ready=False,
                mechanism=CDCMechanism.DYNAMODB_STREAMS,
                blocker_reasons=(f"DynamoDB describe_table probe failed: {exc}",),
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
        if connection is None or not hasattr(connection, "scan"):
            return DeterministicSampler.package_sample(table_name, schema_name or "", [], [])
        try:
            resp = connection.scan(TableName=table_name, Limit=min(limit, 100))
            rows = [_deserialize_item(item) for item in resp.get("Items", [])]
            cols = sorted({k for row in rows for k in row.keys()})
            return DeterministicSampler.package_sample(table_name, schema_name or "", cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling DynamoDB table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name or "", str(exc))

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        # No global change-sequence marker; per-item versioning is application-defined.
        return None
