"""
akaalEngine.discovery.strategies.warehouse.clickhouse
========================================================
Canonical ClickHouse discovery strategy (P7A Campaign B).

Introspects `system.databases`/`system.tables`/`system.columns`/`system.parts` --
ClickHouse's real, queryable system tables (not borrowed from any other provider's
catalog conventions). Partitioning is a genuine, first-class MergeTree property
(`PARTITION BY`), truthfully discovered from `system.tables.partition_key`, not modeled
as a generic SQL partition scheme.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Sequence, Tuple

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
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.programmables import ProgrammableInventory
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts, PrimaryKeyFacts
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.warehouse import WarehouseDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.clickhouse")


class ClickHouseDiscoveryStrategy(WarehouseDiscoveryStrategy):
    """ClickHouse physical discovery strategy -- columnar OLAP, system-table introspection."""

    PROVIDER_ID = "clickhouse"

    SYSTEM_DBS = ("system", "information_schema", "INFORMATION_SCHEMA")

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "ClickHouse"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "server_version"):
            try:
                version_str = f"ClickHouse {connection.server_version}"
                parts = str(connection.server_version).split(".")
                major = int(parts[0]) if len(parts) > 0 else 0
                minor = int(parts[1]) if len(parts) > 1 else 0
                patch = int(parts[2]) if len(parts) > 2 else 0
            except Exception:
                pass

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="ClickHouse, Inc.",
            engine_name="ClickHouse",
            system_type="CLICKHOUSE",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Community / Cloud", is_enterprise=False),
            host=spec.host,
            port=spec.port or 8123,
            database_name=spec.database_name or "default",
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        dbs, system_dbs = [], []
        if connection is not None and hasattr(connection, "query"):
            try:
                result = connection.query("SELECT name FROM system.databases ORDER BY name")
                for row in result.result_rows:
                    name = row[0]
                    if name in self.SYSTEM_DBS:
                        system_dbs.append(name)
                    else:
                        dbs.append(name)
            except Exception as exc:
                logger.warning(f"Error discovering ClickHouse databases: {exc}")
                raise

        return NamespaceInventory(
            schemas=tuple(dbs),
            system_schemas=tuple(system_dbs),
            default_schema="default" if "default" in dbs else (dbs[0] if dbs else None),
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
        views = []
        if connection is not None and hasattr(connection, "query"):
            try:
                result = connection.query(
                    "SELECT name, engine, total_rows, total_bytes FROM system.tables WHERE database = %(db)s ORDER BY name",
                    parameters={"db": schema_name},
                )
                for row in result.result_rows:
                    name, engine, total_rows, total_bytes = row[0], row[1], row[2], row[3]
                    if engine and "View" in engine:
                        views.append(TableFacts(name=name, schema_name=schema_name, object_type=ObjectType.VIEW))
                        continue
                    items.append(
                        TableFacts(
                            name=name,
                            schema_name=schema_name,
                            object_type=ObjectType.TABLE,
                            classification=ObjectClassification.USER,
                            row_count_estimate=max(0, int(total_rows or 0)),
                            size_bytes_estimate=max(0, int(total_bytes or 0)),
                            properties={"engine": engine},
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error querying ClickHouse tables in {schema_name}: {exc}")
                raise

        return CatalogPaginator.paginate_sequence(items, cursor=cursor, page_size=page_size, views=tuple(views))

    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        cols = []
        if connection is not None and hasattr(connection, "query"):
            try:
                result = connection.query(
                    "SELECT name, type, position, is_in_primary_key FROM system.columns WHERE database = %(db)s AND table = %(tbl)s ORDER BY position",
                    parameters={"db": schema_name, "tbl": object_name},
                )
                for row in result.result_rows:
                    name, ctype, pos, is_pk = row[0], row[1], row[2], row[3]
                    is_lob = any(t in ctype for t in ("String", "FixedString"))
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=name,
                            ordinal_position=int(pos),
                            native_type=ctype,
                            nullable="Nullable(" in ctype,
                            is_identity=False,
                            is_lob=is_lob,
                        )
                    )
            except Exception as exc:
                logger.warning(f"Error querying ClickHouse structure for {schema_name}.{object_name}: {exc}")
                raise

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
        )

    def discover_programmables(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
    ) -> ProgrammableInventory:
        # ClickHouse has no stored procedures/triggers/UDTs in the classic relational
        # sense; user-defined functions exist but are cluster-global, not per-schema.
        return ProgrammableInventory()

    def discover_partitioning(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> PartitionFacts:
        partition_key = None
        if connection is not None and hasattr(connection, "query"):
            try:
                result = connection.query(
                    "SELECT partition_key FROM system.tables WHERE database = %(db)s AND name = %(tbl)s",
                    parameters={"db": schema_name, "tbl": table_name},
                )
                rows = result.result_rows
                if rows and rows[0][0]:
                    partition_key = rows[0][0]
            except Exception as exc:
                logger.warning(f"Error discovering ClickHouse partition key for {schema_name}.{table_name}: {exc}")

        strategy = PartitionStrategy.EXPRESSION if partition_key else PartitionStrategy.NONE
        key_cols = tuple(c.strip() for c in partition_key.split(",")) if partition_key else ()

        return PartitionFacts(
            table_name=table_name,
            schema_name=schema_name,
            strategy=strategy,
            key_columns=key_cols,
            partitions=(),
        )

    def discover_table_statistics(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> TableSizeFacts:
        row_count, data_bytes = 0, 0
        if connection is not None and hasattr(connection, "query"):
            try:
                result = connection.query(
                    "SELECT total_rows, total_bytes FROM system.tables WHERE database = %(db)s AND name = %(tbl)s",
                    parameters={"db": schema_name, "tbl": table_name},
                )
                rows = result.result_rows
                if rows:
                    row_count = max(0, int(rows[0][0] or 0))
                    data_bytes = max(0, int(rows[0][1] or 0))
            except Exception as exc:
                logger.warning(f"Error querying ClickHouse stats for {schema_name}.{table_name}: {exc}")

        return TableSizeFacts(
            table_name=table_name,
            schema_name=schema_name,
            row_count=row_count,
            count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
            data_bytes=data_bytes,
        )

    def discover_warehouse_context(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        info: dict[str, Any] = {}
        if connection is not None and hasattr(connection, "query"):
            try:
                result = connection.query("SELECT value FROM system.settings WHERE name = 'max_threads'")
                rows = result.result_rows
                if rows:
                    info["max_threads"] = rows[0][0]
            except Exception:
                pass
        return info

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        if connection is not None and hasattr(connection, "query"):
            try:
                result = connection.query("SELECT value FROM system.settings WHERE name = 'readonly'")
                rows = result.result_rows
                if rows and str(rows[0][0]) != "0":
                    return ThreeStatePermission.PROVEN
                return ThreeStatePermission.DENIED
            except Exception:
                return ThreeStatePermission.UNKNOWN
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        ro = self.check_read_only_permissions(connection, spec)
        cat_perm = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "query"):
            try:
                connection.query("SELECT 1 FROM system.tables LIMIT 1")
                cat_perm = ThreeStatePermission.PROVEN
            except Exception:
                cat_perm = ThreeStatePermission.DENIED

        return PermissionAssessment(read_only_verified=ro, metadata_catalog_read=cat_perm)

    def discover_environment(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> ConfigurationFacts:
        return ConfigurationFacts(
            charset=CharsetFacts(server_encoding="UTF-8"),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=None),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        nodes = []
        if connection is not None and hasattr(connection, "query"):
            try:
                result = connection.query("SELECT host_name, host_address, port FROM system.clusters")
                seen = set()
                for row in result.result_rows:
                    key = (row[0], row[2])
                    if key in seen:
                        continue
                    seen.add(key)
                    nodes.append(ClusterNodeFacts(node_id=f"{row[0]}:{row[2]}", host=row[1] or row[0], port=int(row[2]), role=NodeRole.WORKER))
            except Exception:
                pass

        if not nodes:
            nodes = [ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 8123, role=NodeRole.WORKER)]

        return TopologySnapshot(is_clustered=len(nodes) > 1, connected_node_role=NodeRole.WORKER, nodes=tuple(nodes))

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
                blocker_reasons=("ClickHouse connection not established",),
            )
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.POLLING_WATERMARK,
            blocker_reasons=("ClickHouse has no native change-log/binlog mechanism; only watermark-based incremental polling is possible.",),
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
        if connection is None or not hasattr(connection, "query"):
            return DeterministicSampler.package_sample(table_name, schema_name or "", [], [])
        try:
            result = connection.query(f"SELECT * FROM `{schema_name}`.`{table_name}` LIMIT {int(limit)}")
            cols = list(result.column_names)
            rows = [dict(zip(cols, r)) for r in result.result_rows]
            return DeterministicSampler.package_sample(table_name, schema_name or "", cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling ClickHouse table {schema_name}.{table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name or "", str(exc))

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        return None
