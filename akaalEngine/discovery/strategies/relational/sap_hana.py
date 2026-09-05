"""
akaalEngine.discovery.strategies.relational.sap_hana
======================================================
Canonical SAP HANA discovery strategy (P7A Campaign B, provider #41).
Introspects HANA's real SYS catalog: SYS.SCHEMAS, SYS.TABLES, SYS.VIEWS,
SYS.TABLE_COLUMNS, SYS.CONSTRAINTS, SYS.M_TABLES, SYS.M_DATABASE.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

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
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts, PrimaryKeyFacts
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.sap_hana")


class SAPHANADiscoveryStrategy(RelationalDiscoveryStrategy):
    """SAP HANA physical discovery strategy -- in-memory relational database engine."""

    PROVIDER_ID = "sap_hana"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(self, connection: Any, spec: EndpointSpec, route: Optional[ResolvedRoute] = None) -> DiscoveredEndpointIdentity:
        version_str = "SAP HANA"
        major, minor, patch = 0, 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT VERSION FROM SYS.M_DATABASE")
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
                logger.warning(f"Error fetching SAP HANA version: {exc}")
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID, vendor_name="SAP SE", engine_name="SAP HANA", system_type="SAP_HANA",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Enterprise", is_enterprise=True),
            host=spec.host, port=spec.port or 30015, database_name=spec.database_name,
        )

    def discover_namespaces(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> NamespaceInventory:
        schemas, system_schemas = [], []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT SCHEMA_NAME FROM SYS.SCHEMAS ORDER BY SCHEMA_NAME")
                for row in cur.fetchall():
                    name = str(row[0])
                    if name.startswith("SYS") or name.startswith("_SYS") or name == "PUBLIC":
                        system_schemas.append(name)
                    else:
                        schemas.append(name)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error discovering SAP HANA schemas: {exc}")
                raise
        return NamespaceInventory(schemas=tuple(schemas), system_schemas=tuple(system_schemas), default_schema=schemas[0] if schemas else None)

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
                if offset == 0:
                    cur.execute("SELECT VIEW_NAME FROM SYS.VIEWS WHERE SCHEMA_NAME = ? ORDER BY VIEW_NAME", (schema_name,))
                    for row in cur.fetchall():
                        views.append(ViewFacts(name=str(row[0]), schema_name=schema_name, is_materialized=False))
                cur.execute(
                    "SELECT TABLE_NAME, RECORD_COUNT FROM SYS.M_TABLES WHERE SCHEMA_NAME = ? ORDER BY TABLE_NAME LIMIT ? OFFSET ?",
                    (schema_name, page_size + 1, offset),
                )
                rows = cur.fetchall()
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying SAP HANA tables in {schema_name}: {exc}")
                raise
            if len(rows) > page_size:
                has_more = True
                rows = rows[:page_size]
            for r in rows:
                tables.append(TableFacts(name=str(r[0]), schema_name=schema_name, object_type=ObjectType.TABLE, classification=ObjectClassification.USER, row_count_estimate=int(r[1]) if r[1] is not None else 0))
        next_cursor = DiscoveryCursor(schema_index=0, offset=offset + len(tables)).encode() if has_more else None
        return ObjectInventoryPage(items=tuple(tables), views=tuple(views), cursor=next_cursor, is_last_page=not has_more)

    def discover_object_structure(self, connection: Any, spec: EndpointSpec, schema_name: str, object_name: str, context: DiscoveryContext) -> ObjectStructureFacts:
        cols, primary_key = [], None
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute(
                    "SELECT COLUMN_NAME, DATA_TYPE_NAME, IS_NULLABLE, POSITION FROM SYS.TABLE_COLUMNS "
                    "WHERE SCHEMA_NAME = ? AND TABLE_NAME = ? ORDER BY POSITION",
                    (schema_name, object_name),
                )
                for r in cur.fetchall():
                    cols.append(ColumnPhysicalMetadata(name=str(r[0]), ordinal_position=int(r[3]), native_type=str(r[1]).upper(), nullable=(str(r[2]).strip() == "TRUE")))
                cur.execute(
                    "SELECT COLUMN_NAME FROM SYS.CONSTRAINTS WHERE SCHEMA_NAME = ? AND TABLE_NAME = ? AND IS_PRIMARY_KEY = 'TRUE' ORDER BY POSITION",
                    (schema_name, object_name),
                )
                pk_cols = [str(r[0]) for r in cur.fetchall()]
                if pk_cols:
                    primary_key = PrimaryKeyFacts(name=f"{object_name}_pk", table_name=object_name, columns=tuple(pk_cols), schema_name=schema_name)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying SAP HANA structure for {schema_name}.{object_name}: {exc}")
                raise
        return ObjectStructureFacts(table_name=object_name, schema_name=schema_name, columns=tuple(cols), primary_key=primary_key)

    def discover_programmables(self, connection: Any, spec: EndpointSpec, schema_name: str, context: DiscoveryContext) -> ProgrammableInventory:
        return ProgrammableInventory(routines=(), triggers=(), sequences=(), udts=())

    def discover_partitioning(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, context: DiscoveryContext) -> PartitionFacts:
        return PartitionFacts(table_name=table_name, schema_name=schema_name, strategy=PartitionStrategy.NONE, key_columns=(), partitions=())

    def discover_table_statistics(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, context: DiscoveryContext) -> TableSizeFacts:
        row_count, data_bytes = 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT RECORD_COUNT, TABLE_SIZE FROM SYS.M_TABLES WHERE SCHEMA_NAME = ? AND TABLE_NAME = ?", (schema_name, table_name))
                r = cur.fetchone()
                if r:
                    row_count = int(r[0]) if r[0] is not None else 0
                    data_bytes = int(r[1]) if r[1] is not None else 0
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying SAP HANA stats for {schema_name}.{table_name}: {exc}")
        return TableSizeFacts(table_name=table_name, schema_name=schema_name, row_count=row_count, count_accuracy=CountAccuracy.CATALOG_ESTIMATE, data_bytes=data_bytes)

    def check_read_only_permissions(self, connection: Any, spec: EndpointSpec) -> ThreeStatePermission:
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> PermissionAssessment:
        cat_read = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT 1 FROM SYS.SCHEMAS LIMIT 1")
                cur.fetchone()
                cur.close()
                cat_read = ThreeStatePermission.PROVEN
            except Exception:
                cat_read = ThreeStatePermission.DENIED
        return PermissionAssessment(read_only_verified=ThreeStatePermission.UNKNOWN, metadata_catalog_read=cat_read)

    def discover_environment(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> ConfigurationFacts:
        return ConfigurationFacts(charset=CharsetFacts(server_encoding="UTF-8"), timezone=TimezoneFacts(database_timezone="UTC"), limits=LimitsFacts(max_connections=None))

    def discover_topology(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> TopologySnapshot:
        nodes = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT HOST, SERVICE_STATUS FROM SYS.M_SERVICES WHERE SERVICE_NAME = 'indexserver'")
                for r in cur.fetchall():
                    nodes.append(ClusterNodeFacts(node_id=str(r[0]), host=str(r[0]), port=spec.port or 30015, role=NodeRole.WORKER if str(r[1]).upper() == "STARTED" else NodeRole.UNKNOWN))
                cur.close()
            except Exception as exc:
                logger.warning(f"Error discovering SAP HANA topology: {exc}")
        if not nodes:
            nodes = [ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 30015, role=NodeRole.PRIMARY)]
        return TopologySnapshot(is_clustered=len(nodes) > 1, connected_node_role=NodeRole.PRIMARY, nodes=tuple(nodes))

    def discover_cdc_prerequisites(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> CDCPrerequisiteSnapshot:
        return CDCPrerequisiteSnapshot(is_cdc_ready=False, mechanism=CDCMechanism.UNSUPPORTED, blocker_reasons=("No SAP HANA CDC capture module implemented in this Engine (SLT/SDI are separate SAP products).",))

    def sample_data(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, limit: int = 100, timeout_seconds: float = 3.0) -> SampledRecordSet:
        if connection is None or not hasattr(connection, "cursor"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            cur = connection.cursor()
            cur.execute(f'SELECT TOP {int(limit)} * FROM "{schema_name}"."{table_name}"')
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.close()
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling SAP HANA table {schema_name}.{table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

    def get_schema_change_marker(self, connection: Any, spec: EndpointSpec) -> Optional[str]:
        return None
