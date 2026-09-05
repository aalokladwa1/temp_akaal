"""
akaalEngine.discovery.strategies.relational.teradata
======================================================
Canonical Teradata discovery strategy (P7A Campaign B, provider #39).
Introspects Teradata's real Data Dictionary views: DBC.DatabasesV, DBC.TablesV,
DBC.ColumnsV, DBC.IndicesV, DBC.TableSizeV, DBC.DBCInfoV. Teradata has no
WAL/logical-replication concept usable for generic CDC (FastExport/TPT change-tracking
is a separate licensed product not implemented here).
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import DiscoveryCursor
from akaalEngine.discovery.core.sampling import DeterministicSampler
from akaalEngine.discovery.models.cdc import CDCMechanism, CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import CharsetFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts, ViewFacts
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.programmables import ProgrammableInventory
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, IndexFacts, ObjectStructureFacts, PrimaryKeyFacts
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.teradata")


class TeradataDiscoveryStrategy(RelationalDiscoveryStrategy):
    """Teradata physical discovery strategy -- MPP relational data warehouse."""

    PROVIDER_ID = "teradata"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(self, connection: Any, spec: EndpointSpec, route: Optional[ResolvedRoute] = None) -> DiscoveredEndpointIdentity:
        version_str = "Teradata"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT InfoData FROM DBC.DBCInfoV WHERE InfoKey = 'VERSION'")
                row = cur.fetchone()
                if row:
                    version_str = str(row[0])
                    parts = version_str.split(".")
                    try:
                        major, minor = int(parts[0]), int(parts[1])
                        patch = int(parts[2]) if len(parts) > 2 else 0
                    except (ValueError, IndexError):
                        pass
                cur.close()
            except Exception as exc:
                logger.warning(f"Error fetching Teradata version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Teradata Corporation",
            engine_name="Teradata",
            system_type="TERADATA",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Enterprise", is_enterprise=True),
            host=spec.host,
            port=spec.port or 1025,
            database_name=spec.database_name,
        )

    def discover_namespaces(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> NamespaceInventory:
        schemas, system_schemas = [], []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT DatabaseName FROM DBC.DatabasesV ORDER BY DatabaseName")
                for row in cur.fetchall():
                    name = str(row[0]).strip()
                    if name.startswith("DBC") or name.startswith("SYS") or name.startswith("TD_"):
                        system_schemas.append(name)
                    else:
                        schemas.append(name)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error discovering Teradata databases: {exc}")
                raise
        return NamespaceInventory(schemas=tuple(schemas), system_schemas=tuple(system_schemas), default_schema=spec.database_name)

    def discover_objects_page(self, connection: Any, spec: EndpointSpec, schema_name: str, context: DiscoveryContext, cursor: Optional[str] = None, page_size: int = 500) -> ObjectInventoryPage:
        offset = 0
        if cursor:
            try:
                offset = DiscoveryCursor.decode(cursor).offset
            except Exception:
                offset = 0
        tables, views = [], []
        has_more = False
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute(
                    "SELECT TableName, TableKind FROM DBC.TablesV WHERE DatabaseName = ? AND TableKind IN ('T','V') ORDER BY TableName",
                    (schema_name,),
                )
                rows = cur.fetchall()
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying Teradata tables in {schema_name}: {exc}")
                raise
            page = rows[offset: offset + page_size]
            has_more = (offset + page_size) < len(rows)
            for r in page:
                name, kind = str(r[0]).strip(), str(r[1]).strip()
                if kind == "V":
                    views.append(ViewFacts(name=name, schema_name=schema_name, is_materialized=False))
                else:
                    tables.append(TableFacts(name=name, schema_name=schema_name, object_type=ObjectType.TABLE, classification=ObjectClassification.USER))

        next_cursor = DiscoveryCursor(schema_index=0, offset=offset + page_size).encode() if has_more else None
        return ObjectInventoryPage(items=tuple(tables), views=tuple(views), cursor=next_cursor, is_last_page=not has_more)

    def discover_object_structure(self, connection: Any, spec: EndpointSpec, schema_name: str, object_name: str, context: DiscoveryContext) -> ObjectStructureFacts:
        cols, primary_key, indexes = [], None, []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute(
                    "SELECT ColumnName, ColumnType, Nullable, ColumnId FROM DBC.ColumnsV "
                    "WHERE DatabaseName = ? AND TableName = ? ORDER BY ColumnId",
                    (schema_name, object_name),
                )
                for r in cur.fetchall():
                    name, ctype, nullable, ordinal = str(r[0]).strip(), str(r[1]).strip(), r[2], r[3]
                    cols.append(ColumnPhysicalMetadata(name=name, ordinal_position=int(ordinal), native_type=ctype, nullable=(str(nullable).strip() == "Y")))

                cur.execute(
                    "SELECT ColumnName FROM DBC.IndicesV WHERE DatabaseName = ? AND TableName = ? AND IndexType = 'P' ORDER BY ColumnPosition",
                    (schema_name, object_name),
                )
                pk_cols = [str(r[0]).strip() for r in cur.fetchall()]
                if pk_cols:
                    primary_key = PrimaryKeyFacts(name=f"{object_name}_pk", table_name=object_name, columns=tuple(pk_cols), schema_name=schema_name)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying Teradata structure for {schema_name}.{object_name}: {exc}")
                raise
        return ObjectStructureFacts(table_name=object_name, schema_name=schema_name, columns=tuple(cols), primary_key=primary_key, indexes=tuple(indexes))

    def discover_programmables(self, connection: Any, spec: EndpointSpec, schema_name: str, context: DiscoveryContext) -> ProgrammableInventory:
        return ProgrammableInventory(routines=(), triggers=(), sequences=(), udts=())

    def discover_partitioning(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, context: DiscoveryContext) -> PartitionFacts:
        return PartitionFacts(table_name=table_name, schema_name=schema_name, strategy=PartitionStrategy.NONE, key_columns=(), partitions=())

    def discover_table_statistics(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, context: DiscoveryContext) -> TableSizeFacts:
        data_bytes = 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT SUM(CurrentPerm) FROM DBC.TableSizeV WHERE DatabaseName = ? AND TableName = ?", (schema_name, table_name))
                row = cur.fetchone()
                if row and row[0] is not None:
                    data_bytes = int(row[0])
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying Teradata stats for {schema_name}.{table_name}: {exc}")
        return TableSizeFacts(table_name=table_name, schema_name=schema_name, row_count=0, count_accuracy=CountAccuracy.UNAVAILABLE, data_bytes=data_bytes)

    def check_read_only_permissions(self, connection: Any, spec: EndpointSpec) -> ThreeStatePermission:
        return ThreeStatePermission.UNKNOWN  # Teradata has no session-level read-only flag exposed generically

    def discover_permissions(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> PermissionAssessment:
        cat_read = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT DatabaseName FROM DBC.DatabasesV WHERE DatabaseName = 'DBC'")
                cur.fetchone()
                cur.close()
                cat_read = ThreeStatePermission.PROVEN
            except Exception:
                cat_read = ThreeStatePermission.DENIED
        return PermissionAssessment(read_only_verified=ThreeStatePermission.UNKNOWN, metadata_catalog_read=cat_read)

    def discover_environment(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> ConfigurationFacts:
        return ConfigurationFacts(charset=CharsetFacts(server_encoding="UTF-8"), timezone=TimezoneFacts(database_timezone="UTC"), limits=LimitsFacts(max_connections=None))

    def discover_topology(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> TopologySnapshot:
        node = ClusterNodeFacts(node_id="teradata_amp_node", host=spec.host or "localhost", port=spec.port or 1025, role=NodeRole.WORKER)
        return TopologySnapshot(is_clustered=True, connected_node_role=NodeRole.WORKER, nodes=(node,))

    def discover_cdc_prerequisites(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> CDCPrerequisiteSnapshot:
        return CDCPrerequisiteSnapshot(
            is_cdc_ready=False,
            mechanism=CDCMechanism.UNSUPPORTED,
            blocker_reasons=("No Teradata CDC capture module implemented in this Engine (FastExport/TPT change-tracking is a separate licensed product).",),
        )

    def sample_data(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, limit: int = 100, timeout_seconds: float = 3.0) -> SampledRecordSet:
        if connection is None or not hasattr(connection, "cursor"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            cur = connection.cursor()
            cur.execute(f"SELECT TOP {int(limit)} * FROM \"{schema_name}\".\"{table_name}\"")
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.close()
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling Teradata table {schema_name}.{table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

    def get_schema_change_marker(self, connection: Any, spec: EndpointSpec) -> Optional[str]:
        return None
