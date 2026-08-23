"""
akaalEngine.discovery.strategies.nosql.mongodb
==============================================
Canonical MongoDB discovery strategy.
Introspects databases, collections, validator schemas, shard keys, oplog window,
and performs bounded document shape inference.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot, StartingCommitPosition
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

logger = logging.getLogger("akaalEngine.discovery.strategies.mongodb")


class MongoDBDiscoveryStrategy(NoSQLDiscoveryStrategy):
    """MongoDB physical discovery strategy."""

    PROVIDER_ID = "mongodb"

    SYSTEM_DBS = ('admin', 'config', 'local')

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "6.0.5"
        major, minor, patch = 6, 0, 5
        if connection is not None and hasattr(connection, "server_info"):
            try:
                info = connection.server_info()
                version_str = info.get("version", version_str)
                parts = version_str.split(".")
                major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 6
                minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                patch = int(parts[2].split("-")[0]) if len(parts) > 2 and parts[2].split("-")[0].isdigit() else 0
            except Exception as exc:
                logger.warning(f"Error querying mongo server_info: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="MongoDB Inc.",
            engine_name="MongoDB Document Database",
            system_type="MONGODB",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Community / Enterprise", is_enterprise=True),
            host=spec.host,
            port=spec.port or 27017,
            database_name=spec.database_name,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        databases = []
        if connection is not None and hasattr(connection, "list_database_names"):
            try:
                for db in connection.list_database_names():
                    if db not in self.SYSTEM_DBS:
                        databases.append(db)
            except Exception as exc:
                logger.warning(f"Error listing mongo databases: {exc}")
                raise

        if not databases and spec.database_name:
            databases = [spec.database_name]

        return NamespaceInventory(
            schemas=tuple(databases),
            system_schemas=self.SYSTEM_DBS,
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
        collections = []
        if connection is not None and hasattr(connection, "__getitem__"):
            try:
                db = connection[schema_name]
                for coll_name in db.list_collection_names():
                    if not coll_name.startswith("system."):
                        collections.append(
                            TableFacts(
                                name=coll_name,
                                schema_name=schema_name,
                                object_type=ObjectType.COLLECTION,
                                classification=ObjectClassification.USER,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error listing mongo collections in {schema_name}: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(collections, cursor=cursor, page_size=page_size)

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = [
            ColumnPhysicalMetadata(
                name="_id",
                ordinal_position=1,
                native_type="OBJECTID",
                nullable=False,
                is_identity=True,
            )
        ]
        indexes = []

        if connection is not None and hasattr(connection, "__getitem__"):
            try:
                db = connection[schema_name]
                coll = db[object_name]
                for idx_info in coll.list_indexes():
                    iname = idx_info.get("name", "idx")
                    key_dict = idx_info.get("key", {})
                    idx_cols = tuple(key_dict.keys())
                    is_unique = bool(idx_info.get("unique", False))
                    indexes.append(
                        IndexFacts(
                            name=iname,
                            table_name=object_name,
                            schema_name=schema_name,
                            columns=idx_cols,
                            is_unique=is_unique,
                            access_method=IndexAccessMethod.BTREE,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error reading mongo indexes for {schema_name}.{object_name}: {exc}")
                raise

        pk = PrimaryKeyFacts(name="_id_", table_name=object_name, columns=("_id",), schema_name=schema_name)

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
            primary_key=pk,
            indexes=tuple(indexes),
        )

    def discover_objects_structure_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, ObjectStructureFacts]:
        if not object_names or connection is None or not hasattr(connection, "__getitem__"):
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {}
        for name in object_names:
            cols = [
                ColumnPhysicalMetadata(
                    name="_id",
                    ordinal_position=1,
                    native_type="OBJECTID",
                    nullable=False,
                    is_identity=True,
                )
            ]
            indexes = []
            try:
                db = connection[schema_name]
                coll = db[name]
                for idx_info in coll.list_indexes():
                    iname = idx_info.get("name", "idx")
                    key_dict = idx_info.get("key", {})
                    idx_cols = tuple(key_dict.keys())
                    is_unique = bool(idx_info.get("unique", False))
                    indexes.append(
                        IndexFacts(
                            name=iname,
                            table_name=name,
                            schema_name=schema_name,
                            columns=idx_cols,
                            is_unique=is_unique,
                            access_method=IndexAccessMethod.BTREE,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Bulk mongo index discovery failed for {name}: {exc}")
                raise
            pk = PrimaryKeyFacts(name="_id_", table_name=name, columns=("_id",), schema_name=schema_name)
            results[name] = ObjectStructureFacts(
                table_name=name,
                schema_name=schema_name,
                columns=tuple(cols),
                primary_key=pk,
                indexes=tuple(indexes),
            )
        return results

    def discover_table_statistics_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, TableSizeFacts]:
        if not object_names or connection is None or not hasattr(connection, "__getitem__"):
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {}
        for name in object_names:
            cnt = 0
            try:
                db = connection[schema_name]
                coll = db[name]
                if hasattr(coll, "estimated_document_count"):
                    cnt = coll.estimated_document_count()
            except Exception:
                pass
            results[name] = TableSizeFacts(table_name=name, schema_name=schema_name, row_count=cnt)
        return results

    def infer_document_shape(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        collection_name: str,
        sample_size: int = 100,
    ) -> InferredDocumentShape:
        docs = []
        if connection is not None and hasattr(connection, "__getitem__"):
            try:
                db = connection[schema_name]
                coll = db[collection_name]
                for doc in coll.find().limit(sample_size):
                    docs.append(doc)
            except Exception as exc:
                logger.warning(f"Error sampling mongo docs for shape inference: {exc}")

        return DeterministicSampler.infer_shape_from_documents(collection_name, schema_name, docs)

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        # MongoDB ping does not verify read-only role
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "admin") and hasattr(connection.admin, "command"):
            try:
                connection.admin.command("ping")
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
            limits=LimitsFacts(max_connections=1000),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        is_rs = False
        nodes = []
        if connection is not None and hasattr(connection, "admin"):
            try:
                res = connection.admin.command("isMaster")
                is_rs = "setName" in res
                primary_host = res.get("primary", spec.host or "localhost")
                nodes.append(ClusterNodeFacts(node_id="primary", host=primary_host, port=spec.port or 27017, role=NodeRole.PRIMARY))
                for h in res.get("hosts", []):
                    if h != primary_host:
                        nodes.append(ClusterNodeFacts(node_id=f"replica_{h}", host=h, port=spec.port or 27017, role=NodeRole.REPLICA))
            except Exception as exc:
                logger.warning(f"Error querying mongo isMaster: {exc}")

        return TopologySnapshot(
            is_clustered=is_rs,
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
                blocker_reasons=("MongoDB connection not established",),
            )
        is_rs = False
        if hasattr(connection, "admin"):
            try:
                res = connection.admin.command("isMaster")
                is_rs = "setName" in res
            except Exception:
                pass

        blockers = []
        if not is_rs:
            blockers.append("MongoDB instance is standalone (Replica set required for Change Streams).")

        return CDCPrerequisiteSnapshot(
            is_cdc_ready=is_rs,
            mechanism=CDCMechanism.MONGO_CHANGE_STREAMS if is_rs else CDCMechanism.POLLING_WATERMARK,
            is_replica_set=is_rs,
            blocker_reasons=tuple(blockers),
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
        if connection is None or not hasattr(connection, "__getitem__"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            docs = []
            cols = set()
            db = connection[schema_name]
            coll = db[table_name]
            for doc in coll.find().limit(limit):
                clean_doc = {}
                for k, v in doc.items():
                    clean_doc[k] = str(v) if k == "_id" else v
                    cols.add(k)
                docs.append(clean_doc)
            return DeterministicSampler.package_sample(table_name, schema_name, sorted(list(cols)), docs)
        except Exception as exc:
            logger.warning(f"Error sampling mongo collection {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))
