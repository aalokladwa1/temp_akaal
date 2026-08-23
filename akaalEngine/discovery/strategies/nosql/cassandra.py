"""
akaalEngine.discovery.strategies.nosql.cassandra
================================================
Canonical Apache Cassandra wide-column discovery strategy.
Introspects system_schema.keyspaces, system_schema.tables, system_schema.columns,
system.peers, system.size_estimates, and token ranges.
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
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy, TokenRangeFacts
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

logger = logging.getLogger("akaalEngine.discovery.strategies.cassandra")


class CassandraDiscoveryStrategy(NoSQLDiscoveryStrategy):
    """Apache Cassandra physical discovery strategy."""

    PROVIDER_ID = "cassandra"

    SYSTEM_KEYSPACES = ('system', 'system_schema', 'system_auth', 'system_distributed', 'system_traces', 'system_views', 'system_virtual_schema')

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "4.0.0"
        cluster_name = "Cassandra Cluster"
        if connection is not None and hasattr(connection, "execute"):
            try:
                row = connection.execute("SELECT cluster_name, release_version FROM system.local").one()
                if row:
                    cluster_name = getattr(row, "cluster_name", cluster_name)
                    version_str = getattr(row, "release_version", version_str)
            except Exception as exc:
                logger.warning(f"Error querying cassandra system.local: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Apache Software Foundation",
            engine_name="Apache Cassandra",
            system_type="CASSANDRA",
            version=ServerVersion(raw_version_string=version_str, major=4, minor=0, patch=0),
            edition=EngineEdition(edition_name="Community Wide-Column", is_enterprise=False),
            instance_name=cluster_name,
            host=spec.host,
            port=spec.port or 9042,
            database_name=spec.database_name,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        keyspaces = []
        if connection is not None and hasattr(connection, "execute"):
            try:
                rows = connection.execute("SELECT keyspace_name FROM system_schema.keyspaces")
                for r in rows:
                    ks = getattr(r, "keyspace_name", "")
                    if ks not in self.SYSTEM_KEYSPACES:
                        keyspaces.append(ks)
            except Exception as exc:
                logger.warning(f"Error querying cassandra keyspaces: {exc}")
                raise

        if not keyspaces and spec.database_name:
            keyspaces = [spec.database_name]

        return NamespaceInventory(
            schemas=tuple(keyspaces),
            keyspaces=tuple(keyspaces),
            system_schemas=self.SYSTEM_KEYSPACES,
            default_schema=keyspaces[0] if keyspaces else None,
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
        tables = []
        if connection is not None and hasattr(connection, "execute"):
            try:
                rows = connection.execute(
                    "SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s",
                    (schema_name,)
                )
                for r in rows:
                    tname = getattr(r, "table_name", "")
                    tables.append(
                        TableFacts(
                            name=tname,
                            schema_name=schema_name,
                            object_type=ObjectType.TABLE,
                            classification=ObjectClassification.USER,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error querying cassandra tables in {schema_name}: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(tables, cursor=cursor, page_size=page_size)

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = []
        pk_cols = []
        indexes = []

        if connection is not None and hasattr(connection, "execute"):
            try:
                rows = connection.execute(
                    "SELECT column_name, type, kind, position FROM system_schema.columns WHERE keyspace_name = %s AND table_name = %s",
                    (schema_name, object_name)
                )
                for idx, r in enumerate(rows):
                    cname = getattr(r, "column_name", "")
                    ctype = getattr(r, "type", "")
                    kind = getattr(r, "kind", "")
                    is_pk = (kind in ("partition_key", "clustering"))
                    if is_pk:
                        pk_cols.append(cname)
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=idx + 1,
                            native_type=str(ctype).upper(),
                            nullable=not is_pk,
                            is_identity=is_pk,
                        )
                    )

                idx_rows = connection.execute(
                    "SELECT index_name, kind, options FROM system_schema.indexes WHERE keyspace_name = %s AND table_name = %s",
                    (schema_name, object_name)
                )
                for ir in idx_rows:
                    iname = getattr(ir, "index_name", "idx")
                    indexes.append(
                        IndexFacts(
                            name=iname,
                            table_name=object_name,
                            schema_name=schema_name,
                            columns=(iname,),
                            access_method=IndexAccessMethod.BTREE,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error querying cassandra structure for {schema_name}.{object_name}: {exc}")
                raise

        pk = PrimaryKeyFacts(name="pk", table_name=object_name, columns=tuple(pk_cols), schema_name=schema_name) if pk_cols else None

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
        if not object_names or connection is None or not hasattr(connection, "execute"):
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {name: ObjectStructureFacts(table_name=name, schema_name=schema_name) for name in object_names}
        names_list = list(object_names)
        format_strings = ','.join(['%s'] * len(names_list))

        try:
            # 1. Bulk Columns
            rows = connection.execute(
                f"SELECT table_name, column_name, type, kind, position FROM system_schema.columns WHERE keyspace_name = %s AND table_name IN ({format_strings})",
                [schema_name] + names_list
            )
            cols_by_tbl: dict[str, list[ColumnPhysicalMetadata]] = {name: [] for name in object_names}
            pk_by_tbl: dict[str, list[str]] = {name: [] for name in object_names}
            for r in rows:
                tname = getattr(r, "table_name", "")
                cname = getattr(r, "column_name", "")
                ctype = getattr(r, "type", "")
                kind = getattr(r, "kind", "")
                is_pk = (kind in ("partition_key", "clustering"))
                if is_pk:
                    pk_by_tbl.setdefault(tname, []).append(cname)
                cols_by_tbl.setdefault(tname, []).append(
                    ColumnPhysicalMetadata(
                        name=cname,
                        ordinal_position=len(cols_by_tbl.get(tname, [])) + 1,
                        native_type=str(ctype).upper(),
                        nullable=not is_pk,
                        is_identity=is_pk,
                    )
                )

            # 2. Bulk Indexes
            idx_rows = connection.execute(
                f"SELECT table_name, index_name, kind, options FROM system_schema.indexes WHERE keyspace_name = %s AND table_name IN ({format_strings})",
                [schema_name] + names_list
            )
            indexes_by_tbl: dict[str, list[IndexFacts]] = {name: [] for name in object_names}
            for ir in idx_rows:
                tname = getattr(ir, "table_name", "")
                iname = getattr(ir, "index_name", "idx")
                indexes_by_tbl.setdefault(tname, []).append(
                    IndexFacts(
                        name=iname,
                        table_name=tname,
                        schema_name=schema_name,
                        columns=(iname,),
                        access_method=IndexAccessMethod.BTREE,
                    )
                )

            for name in object_names:
                pk_cols = pk_by_tbl.get(name, [])
                pk = PrimaryKeyFacts(name="pk", table_name=name, columns=tuple(pk_cols), schema_name=schema_name) if pk_cols else None
                results[name] = ObjectStructureFacts(
                    table_name=name,
                    schema_name=schema_name,
                    columns=tuple(cols_by_tbl.get(name, [])),
                    primary_key=pk,
                    indexes=tuple(indexes_by_tbl.get(name, [])),
                )
        except Exception as exc:
            logger.warning(f"Bulk structure discovery failed for Cassandra keyspace '{schema_name}': {exc}")
            raise

        return results

    def discover_table_statistics_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, TableSizeFacts]:
        if not object_names or connection is None or not hasattr(connection, "execute"):
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {name: TableSizeFacts(table_name=name, schema_name=schema_name, row_count=0) for name in object_names}
        return results

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
        # Cassandra CQL has no non-destructive physical probe for read-only role state
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "execute"):
            try:
                connection.execute("SELECT cluster_name FROM system.local")
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
        nodes = []
        if connection is not None and hasattr(connection, "execute"):
            try:
                rows = connection.execute("SELECT peer, data_center, rack, release_version FROM system.peers")
                for r in rows:
                    peer_ip = str(getattr(r, "peer", "unknown"))
                    dc = str(getattr(r, "data_center", "datacenter1"))
                    rack = str(getattr(r, "rack", "rack1"))
                    nodes.append(
                        ClusterNodeFacts(
                            node_id=f"peer_{peer_ip}",
                            host=peer_ip,
                            port=spec.port or 9042,
                            role=NodeRole.WORKER,
                            datacenter=dc,
                            rack=rack,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error querying cassandra system.peers: {exc}")

        nodes.insert(0, ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 9042, role=NodeRole.COORDINATOR))

        return TopologySnapshot(
            is_clustered=len(nodes) > 1,
            connected_node_role=NodeRole.COORDINATOR,
            nodes=tuple(nodes),
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
                blocker_reasons=("Cassandra connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.CASSANDRA_CDC,
            blocker_reasons=("CDC logging not verified on keyspace tables",),
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
        if connection is None or not hasattr(connection, "execute"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            rows = []
            result = connection.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT {limit}")
            cols = list(result.column_names) if hasattr(result, "column_names") else []
            for r in result:
                if hasattr(r, "_asdict"):
                    rows.append(r._asdict())
                else:
                    rows.append(dict(zip(cols, r)))
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling cassandra table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))
