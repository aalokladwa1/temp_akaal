"""
akaalEngine.discovery.strategies.relational.sap_ase
=====================================================
Canonical SAP ASE (Sybase Adaptive Server Enterprise) discovery strategy
(P7A Campaign B, provider #42). Introspects ASE's real system catalog:
sysdatabases, sysobjects, syscolumns, sysindexes -- ASE has no information_schema by
default, so this strategy queries the native catalog, not a borrowed one.
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
from akaalEngine.discovery.models.structure import ColumnPhysicalMetadata, ObjectStructureFacts
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.sap_ase")


class SAPASEDiscoveryStrategy(RelationalDiscoveryStrategy):
    """SAP ASE physical discovery strategy -- TDS-family relational database."""

    PROVIDER_ID = "sap_ase"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(self, connection: Any, spec: EndpointSpec, route: Optional[ResolvedRoute] = None) -> DiscoveredEndpointIdentity:
        version_str = "SAP ASE"
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT @@version")
                row = cur.fetchone()
                if row:
                    version_str = str(row[0])
                cur.close()
            except Exception as exc:
                logger.warning(f"Error fetching SAP ASE version: {exc}")
        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID, vendor_name="SAP SE", engine_name="SAP ASE", system_type="SAP_ASE",
            version=ServerVersion(raw_version_string=version_str, major=0, minor=0, patch=0),
            edition=EngineEdition(edition_name="Enterprise", is_enterprise=True),
            host=spec.host, port=spec.port or 5000, database_name=spec.database_name,
        )

    def discover_namespaces(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> NamespaceInventory:
        schemas, system_schemas = [], []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT name FROM master..sysdatabases ORDER BY name")
                for row in cur.fetchall():
                    name = str(row[0])
                    if name in ("master", "model", "tempdb", "sybsystemprocs", "sybsystemdb"):
                        system_schemas.append(name)
                    else:
                        schemas.append(name)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error discovering SAP ASE databases: {exc}")
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
                cur.execute("SELECT name, type FROM sysobjects WHERE type IN ('U','V') ORDER BY name")
                rows = cur.fetchall()
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying SAP ASE objects in {schema_name}: {exc}")
                raise
            page = rows[offset: offset + page_size]
            has_more = (offset + page_size) < len(rows)
            for r in page:
                name, otype = str(r[0]).strip(), str(r[1]).strip()
                if otype == "V":
                    views.append(ViewFacts(name=name, schema_name=schema_name, is_materialized=False))
                else:
                    tables.append(TableFacts(name=name, schema_name=schema_name, object_type=ObjectType.TABLE, classification=ObjectClassification.USER))
        next_cursor = DiscoveryCursor(schema_index=0, offset=offset + page_size).encode() if has_more else None
        return ObjectInventoryPage(items=tuple(tables), views=tuple(views), cursor=next_cursor, is_last_page=not has_more)

    def discover_object_structure(self, connection: Any, spec: EndpointSpec, schema_name: str, object_name: str, context: DiscoveryContext) -> ObjectStructureFacts:
        cols = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute(
                    "SELECT c.name, t.name, c.colid, c.status FROM syscolumns c "
                    "JOIN systypes t ON c.usertype = t.usertype "
                    "WHERE c.id = OBJECT_ID(?) ORDER BY c.colid",
                    (object_name,),
                )
                for r in cur.fetchall():
                    name, native_type, ordinal, status = str(r[0]).strip(), str(r[1]).strip(), int(r[2]), r[3]
                    nullable = bool(int(status) & 8) if status is not None else True
                    cols.append(ColumnPhysicalMetadata(name=name, ordinal_position=ordinal, native_type=native_type.upper(), nullable=nullable))
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying SAP ASE structure for {schema_name}.{object_name}: {exc}")
                raise
        return ObjectStructureFacts(table_name=object_name, schema_name=schema_name, columns=tuple(cols))

    def discover_programmables(self, connection: Any, spec: EndpointSpec, schema_name: str, context: DiscoveryContext) -> ProgrammableInventory:
        return ProgrammableInventory(routines=(), triggers=(), sequences=(), udts=())

    def discover_partitioning(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, context: DiscoveryContext) -> PartitionFacts:
        return PartitionFacts(table_name=table_name, schema_name=schema_name, strategy=PartitionStrategy.NONE, key_columns=(), partitions=())

    def discover_table_statistics(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, context: DiscoveryContext) -> TableSizeFacts:
        row_count = 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT rowcnt(doampg) FROM sysindexes WHERE id = OBJECT_ID(?) AND indid IN (0,1)", (table_name,))
                r = cur.fetchone()
                if r and r[0] is not None:
                    row_count = int(r[0])
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying SAP ASE stats for {schema_name}.{table_name}: {exc}")
        return TableSizeFacts(table_name=table_name, schema_name=schema_name, row_count=row_count, count_accuracy=CountAccuracy.CATALOG_ESTIMATE)

    def check_read_only_permissions(self, connection: Any, spec: EndpointSpec) -> ThreeStatePermission:
        return ThreeStatePermission.UNKNOWN

    def discover_permissions(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> PermissionAssessment:
        cat_read = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT 1 FROM master..sysdatabases WHERE name = 'master'")
                cur.fetchone()
                cur.close()
                cat_read = ThreeStatePermission.PROVEN
            except Exception:
                cat_read = ThreeStatePermission.DENIED
        return PermissionAssessment(read_only_verified=ThreeStatePermission.UNKNOWN, metadata_catalog_read=cat_read)

    def discover_environment(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> ConfigurationFacts:
        return ConfigurationFacts(charset=CharsetFacts(server_encoding="UTF-8"), timezone=TimezoneFacts(database_timezone="UTC"), limits=LimitsFacts(max_connections=None))

    def discover_topology(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> TopologySnapshot:
        node = ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 5000, role=NodeRole.PRIMARY)
        return TopologySnapshot(is_clustered=False, connected_node_role=NodeRole.PRIMARY, nodes=(node,))

    def discover_cdc_prerequisites(self, connection: Any, spec: EndpointSpec, context: DiscoveryContext) -> CDCPrerequisiteSnapshot:
        return CDCPrerequisiteSnapshot(is_cdc_ready=False, mechanism=CDCMechanism.UNSUPPORTED, blocker_reasons=("No SAP ASE CDC capture module implemented in this Engine (SAP Replication Server is a separate product).",))

    def sample_data(self, connection: Any, spec: EndpointSpec, schema_name: str, table_name: str, limit: int = 100, timeout_seconds: float = 3.0) -> SampledRecordSet:
        if connection is None or not hasattr(connection, "cursor"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            cur = connection.cursor()
            cur.execute(f"SELECT TOP {int(limit)} * FROM {schema_name}.{table_name}")
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.close()
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling SAP ASE table {schema_name}.{table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

    def get_schema_change_marker(self, connection: Any, spec: EndpointSpec) -> Optional[str]:
        return None
