"""
akaalEngine.discovery.strategies.relational.mssql
================================================
Canonical Microsoft SQL Server discovery strategy.
Introspects sys.schemas, sys.tables, sys.columns, sys.foreign_keys, sys.indexes,
sys.partitions, AlwaysOn Availability Groups, and CDC/Change Tracking.
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
from akaalEngine.discovery.models.environment import CharsetFacts, CollationFacts, ConfigurationFacts, LimitsFacts, TimezoneFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity, EngineEdition, ServerVersion
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts
from akaalEngine.discovery.models.partitioning import PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, PrivilegeFact, ThreeStatePermission
from akaalEngine.discovery.models.programmables import ProgrammableInventory, RoutineFacts, RoutineType
from akaalEngine.discovery.models.statistics import CountAccuracy, TableSizeFacts
from akaalEngine.discovery.models.structure import (
    CheckConstraintFacts,
    ColumnPhysicalMetadata,
    ForeignKeyFacts,
    IndexAccessMethod,
    IndexFacts,
    ObjectStructureFacts,
    PrimaryKeyFacts,
    UniqueConstraintFacts,
)
from akaalEngine.discovery.models.topology import ClusterNodeFacts, NodeRole, TopologySnapshot
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy

logger = logging.getLogger("akaalEngine.discovery.strategies.mssql")


class MSSQLDiscoveryStrategy(RelationalDiscoveryStrategy):
    """Microsoft SQL Server physical discovery strategy."""

    PROVIDER_ID = "mssql"

    SYSTEM_SCHEMAS = ('sys', 'information_schema', 'guest', 'INFORMATION_SCHEMA')

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "Microsoft SQL Server 2022"
        major, minor, patch = 16, 0, 0
        instance_name = None
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT @@VERSION, SERVERPROPERTY('ProductVersion'), SERVERPROPERTY('ServerName')")
                r = cur.fetchone()
                if r:
                    version_str = str(r[0])
                    pver = str(r[1])
                    instance_name = str(r[2])
                    parts = pver.split(".")
                    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 16
                    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mssql version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Microsoft Corporation",
            engine_name="Microsoft SQL Server",
            system_type="MSSQL",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Enterprise / Standard", is_enterprise=True),
            instance_name=instance_name,
            host=spec.host,
            port=spec.port or 1433,
            database_name=spec.database_name,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        schemas = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT name FROM sys.schemas WHERE schema_id < 16384 ORDER BY name")
                for r in cur.fetchall():
                    s = str(r[0])
                    if s.lower() not in self.SYSTEM_SCHEMAS:
                        schemas.append(s)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mssql schemas: {exc}")
                raise

        return NamespaceInventory(
            schemas=tuple(schemas),
            system_schemas=self.SYSTEM_SCHEMAS,
            default_schema="dbo" if "dbo" in schemas else (schemas[0] if schemas else None),
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
        offset = 0
        if cursor:
            try:
                dec = DiscoveryCursor.decode(cursor)
                offset = dec.offset
            except Exception:
                offset = 0

        tables = []
        views = []
        has_more = False
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                if offset == 0:
                    # Views
                    try:
                        cur.execute("""
                            SELECT v.name, m.definition
                            FROM sys.views v
                            JOIN sys.schemas s ON s.schema_id = v.schema_id
                            LEFT JOIN sys.sql_modules m ON m.object_id = v.object_id
                            WHERE s.name = ?
                            ORDER BY v.name
                        """, (schema_name,))
                        for r in cur.fetchall():
                            vname, vdef = r[0], r[1]
                            views.append(
                                ViewFacts(
                                    name=vname,
                                    schema_name=schema_name,
                                    is_materialized=False,
                                    definition_sql=str(vdef) if vdef else None,
                                )
                            )
                    except Exception:
                        pass

                # Tables with server-side OFFSET / FETCH NEXT pagination
                cur.execute("""
                    SELECT t.name, t.type, COALESCE(SUM(p.rows), 0) AS row_count
                    FROM sys.tables t
                    JOIN sys.schemas s ON s.schema_id = t.schema_id
                    LEFT JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
                    WHERE s.name = ?
                    GROUP BY t.name, t.type
                    ORDER BY t.name
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """, (schema_name, offset, page_size + 1))
                rows = cur.fetchall()
                if len(rows) > page_size:
                    has_more = True
                    rows = rows[:page_size]

                for r in rows:
                    tname, ttype, nrows = r[0], r[1], r[2]
                    tables.append(
                        TableFacts(
                            name=tname,
                            schema_name=schema_name,
                            object_type=ObjectType.TABLE,
                            classification=ObjectClassification.USER,
                            row_count_estimate=int(nrows),
                        )
                    )

                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mssql tables in {schema_name}: {exc}")
                raise

        next_cursor = None
        if has_more:
            next_cursor = DiscoveryCursor(offset=offset + len(tables), generation_token=f"{schema_name}_{offset}").encode()

        return ObjectInventoryPage(
            items=tuple(tables),
            views=tuple(views),
            cursor=next_cursor,
            is_last_page=not has_more,
            total_items_estimate=len(tables) + len(views),
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
        fks = []
        indexes = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                # Columns
                cur.execute("""
                    SELECT c.column_id, c.name, tp.name AS type_name, c.max_length, c.precision, c.scale,
                           c.is_nullable, c.is_identity, c.is_computed, d.definition AS default_val
                    FROM sys.columns c
                    JOIN sys.tables t ON t.object_id = c.object_id
                    JOIN sys.schemas s ON s.schema_id = t.schema_id
                    JOIN sys.types tp ON tp.user_type_id = c.user_type_id
                    LEFT JOIN sys.default_constraints d ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id
                    WHERE s.name = ? AND t.name = ?
                    ORDER BY c.column_id
                """, (schema_name, object_name))
                for r in cur.fetchall():
                    cid, cname, tpname, mlen, prec, scale, nullb, ident, comp, dflt = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]
                    is_lob = any(t in str(tpname).lower() for t in ("varchar(max)", "nvarchar(max)", "varbinary(max)", "text", "image", "xml"))
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=cid,
                            native_type=str(tpname).upper(),
                            length=mlen,
                            precision=prec,
                            scale=scale,
                            nullable=bool(nullb),
                            default_expression=str(dflt) if dflt else None,
                            is_identity=bool(ident),
                            is_computed=bool(comp),
                            is_lob=is_lob,
                        )
                    )

                # Primary Key & Indexes
                cur.execute("""
                    SELECT i.name, i.is_unique, i.is_primary_key, i.type_desc, col.name
                    FROM sys.indexes i
                    JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                    JOIN sys.columns col ON col.object_id = ic.object_id AND col.column_id = ic.column_id
                    JOIN sys.tables t ON t.object_id = i.object_id
                    JOIN sys.schemas s ON s.schema_id = t.schema_id
                    WHERE s.name = ? AND t.name = ?
                    ORDER BY i.name, ic.key_ordinal
                """, (schema_name, object_name))
                idx_map: dict[str, dict[str, Any]] = {}
                for r in cur.fetchall():
                    iname, is_uniq, is_pk, tdesc, colname = r[0], r[1], r[2], r[3], r[4]
                    if iname not in idx_map:
                        idx_map[iname] = {"is_pk": bool(is_pk), "unique": bool(is_uniq), "type": tdesc, "cols": []}
                    idx_map[iname]["cols"].append(colname)

                for iname, info in idx_map.items():
                    if info["is_pk"]:
                        primary_key = PrimaryKeyFacts(name=iname, table_name=object_name, columns=tuple(info["cols"]), schema_name=schema_name)
                    else:
                        indexes.append(
                            IndexFacts(
                                name=iname,
                                table_name=object_name,
                                schema_name=schema_name,
                                columns=tuple(info["cols"]),
                                is_unique=info["unique"],
                                access_method=IndexAccessMethod.CLUSTERED if "CLUSTERED" in str(info["type"]) else IndexAccessMethod.NON_CLUSTERED,
                            )
                        )

                # Foreign Keys
                cur.execute("""
                    SELECT fk.name, c.name, rs.name, rt.name, rc.name
                    FROM sys.foreign_keys fk
                    JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
                    JOIN sys.tables t ON t.object_id = fk.parent_object_id
                    JOIN sys.schemas s ON s.schema_id = t.schema_id
                    JOIN sys.columns c ON c.object_id = t.object_id AND c.column_id = fkc.parent_column_id
                    JOIN sys.tables rt ON rt.object_id = fk.referenced_object_id
                    JOIN sys.schemas rs ON rs.schema_id = rt.schema_id
                    JOIN sys.columns rc ON rc.object_id = rt.object_id AND rc.column_id = fkc.referenced_column_id
                    WHERE s.name = ? AND t.name = ?
                """, (schema_name, object_name))
                for r in cur.fetchall():
                    fks.append(
                        ForeignKeyFacts(
                            name=r[0],
                            table_name=object_name,
                            columns=(r[1],),
                            referenced_schema=r[2],
                            referenced_table=r[3],
                            referenced_columns=(r[4],),
                            schema_name=schema_name,
                        )
                    )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mssql structure for {schema_name}.{object_name}: {exc}")
                raise

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
            primary_key=primary_key,
            foreign_keys=tuple(fks),
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
        if not object_names or connection is None or not hasattr(connection, "cursor"):
            return super().discover_objects_structure_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, ObjectStructureFacts] = {name: ObjectStructureFacts(table_name=name, schema_name=schema_name) for name in object_names}
        names_list = list(object_names)
        param_placeholders = ','.join(['?'] * len(names_list))

        try:
            cur = connection.cursor()
            # 1. Bulk Columns
            cur.execute(f"""
                SELECT t.name, c.column_id, c.name, tp.name AS type_name, c.max_length, c.precision, c.scale,
                       c.is_nullable, c.is_identity, c.is_computed, d.definition AS default_val
                FROM sys.columns c
                JOIN sys.tables t ON t.object_id = c.object_id
                JOIN sys.schemas s ON s.schema_id = t.schema_id
                JOIN sys.types tp ON tp.user_type_id = c.user_type_id
                LEFT JOIN sys.default_constraints d ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id
                WHERE s.name = ? AND t.name IN ({param_placeholders})
                ORDER BY t.name, c.column_id
            """, [schema_name] + names_list)
            cols_by_tbl: dict[str, list[ColumnPhysicalMetadata]] = {name: [] for name in object_names}
            for r in cur.fetchall():
                tname, cid, cname, tpname, mlen, prec, scale, nullb, ident, comp, dflt = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10]
                is_lob = any(t in str(tpname).lower() for t in ("varchar(max)", "nvarchar(max)", "varbinary(max)", "text", "image", "xml"))
                cols_by_tbl.setdefault(tname, []).append(
                    ColumnPhysicalMetadata(
                        name=cname,
                        ordinal_position=cid,
                        native_type=str(tpname).upper(),
                        length=mlen,
                        precision=prec,
                        scale=scale,
                        nullable=bool(nullb),
                        default_expression=str(dflt) if dflt else None,
                        is_identity=bool(ident),
                        is_computed=bool(comp),
                        is_lob=is_lob,
                    )
                )

            # 2. Bulk Indexes & Primary Keys
            cur.execute(f"""
                SELECT t.name, i.name, i.is_unique, i.is_primary_key, i.type_desc, col.name
                FROM sys.indexes i
                JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                JOIN sys.columns col ON col.object_id = ic.object_id AND col.column_id = ic.column_id
                JOIN sys.tables t ON t.object_id = i.object_id
                JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE s.name = ? AND t.name IN ({param_placeholders})
                ORDER BY t.name, i.name, ic.key_ordinal
            """, [schema_name] + names_list)
            idx_map: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in object_names}
            for r in cur.fetchall():
                tname, iname, is_uniq, is_pk, tdesc, colname = r[0], r[1], r[2], r[3], r[4], r[5]
                t_idx = idx_map.setdefault(tname, {})
                if iname not in t_idx:
                    t_idx[iname] = {"is_pk": bool(is_pk), "unique": bool(is_uniq), "type": tdesc, "cols": []}
                t_idx[iname]["cols"].append(colname)

            pk_by_tbl: dict[str, Optional[PrimaryKeyFacts]] = {}
            indexes_by_tbl: dict[str, list[IndexFacts]] = {name: [] for name in object_names}

            for tname, t_idx in idx_map.items():
                for iname, info in t_idx.items():
                    if info["is_pk"]:
                        pk_by_tbl[tname] = PrimaryKeyFacts(name=iname, table_name=tname, columns=tuple(info["cols"]), schema_name=schema_name)
                    else:
                        indexes_by_tbl.setdefault(tname, []).append(
                            IndexFacts(
                                name=iname,
                                table_name=tname,
                                schema_name=schema_name,
                                columns=tuple(info["cols"]),
                                is_unique=info["unique"],
                                access_method=IndexAccessMethod.CLUSTERED if "CLUSTERED" in str(info["type"]) else IndexAccessMethod.NON_CLUSTERED,
                            )
                        )

            cur.close()
            for name in object_names:
                results[name] = ObjectStructureFacts(
                    table_name=name,
                    schema_name=schema_name,
                    columns=tuple(cols_by_tbl.get(name, [])),
                    primary_key=pk_by_tbl.get(name),
                    indexes=tuple(indexes_by_tbl.get(name, [])),
                )
        except Exception as exc:
            logger.warning(f"Bulk structure discovery failed for MSSQL schema '{schema_name}': {exc}")
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
        if not object_names or connection is None or not hasattr(connection, "cursor"):
            return super().discover_table_statistics_bulk(connection, spec, schema_name, object_names, context)

        results: dict[str, TableSizeFacts] = {name: TableSizeFacts(table_name=name, schema_name=schema_name, row_count=0) for name in object_names}
        names_list = list(object_names)
        param_placeholders = ','.join(['?'] * len(names_list))

        try:
            cur = connection.cursor()
            cur.execute(f"""
                SELECT t.name, COALESCE(SUM(p.rows), 0) AS row_count
                FROM sys.partitions p
                JOIN sys.tables t ON t.object_id = p.object_id
                JOIN sys.schemas s ON s.schema_id = t.schema_id
                WHERE s.name = ? AND t.name IN ({param_placeholders}) AND p.index_id IN (0, 1)
                GROUP BY t.name
            """, [schema_name] + names_list)
            for r in cur.fetchall():
                tname, nrows = r[0], r[1]
                results[tname] = TableSizeFacts(
                    table_name=tname,
                    schema_name=schema_name,
                    row_count=int(nrows or 0),
                    count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
                )
            cur.close()
        except Exception as exc:
            logger.warning(f"Bulk stats discovery failed for MSSQL schema '{schema_name}': {exc}")
            raise

        return results

    def discover_programmables(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
    ) -> ProgrammableInventory:
        routines = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("""
                    SELECT ROUTINE_NAME, ROUTINE_TYPE, ROUTINE_DEFINITION
                    FROM INFORMATION_SCHEMA.ROUTINES
                    WHERE ROUTINE_SCHEMA = ?
                """, (schema_name,))
                for r in cur.fetchall():
                    rname, rtype, rdef = r[0], r[1], r[2]
                    routines.append(
                        RoutineFacts(
                            name=rname,
                            schema_name=schema_name,
                            routine_type=RoutineType.PROCEDURE if "PROCEDURE" in str(rtype).upper() else RoutineType.FUNCTION,
                            definition_sql=rdef,
                        )
                    )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error discovering mssql routines: {exc}")

        return ProgrammableInventory(routines=tuple(routines))

    def discover_partitioning(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> PartitionFacts:
        return PartitionFacts(table_name=table_name, schema_name=schema_name, strategy=PartitionStrategy.NONE)

    def discover_table_statistics(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> TableSizeFacts:
        rows = 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("""
                    SELECT SUM(p.rows)
                    FROM sys.partitions p
                    JOIN sys.tables t ON t.object_id = p.object_id
                    JOIN sys.schemas s ON s.schema_id = t.schema_id
                    WHERE s.name = ? AND t.name = ? AND p.index_id IN (0, 1)
                """, (schema_name, table_name))
                r = cur.fetchone()
                if r and r[0] is not None:
                    rows = int(r[0])
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mssql stats for {table_name}: {exc}")
                raise

        return TableSizeFacts(
            table_name=table_name,
            schema_name=schema_name,
            row_count=rows,
            count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
        )

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        if connection is None:
            return ThreeStatePermission.UNKNOWN
        if hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT DATABASEPROPERTYEX(DB_NAME(), 'Updateability')")
                r = cur.fetchone()
                cur.close()
                if r and str(r[0]).upper() == "READ_ONLY":
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
        ro_verified = self.check_read_only_permissions(connection, spec)
        cat_read = ThreeStatePermission.UNKNOWN
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT name FROM sys.schemas WHERE schema_id = 1")
                cur.fetchall()
                cur.close()
                cat_read = ThreeStatePermission.PROVEN
            except Exception:
                cat_read = ThreeStatePermission.DENIED

        return PermissionAssessment(
            read_only_verified=ro_verified,
            metadata_catalog_read=cat_read,
        )

    def discover_environment(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> ConfigurationFacts:
        collate = "SQL_Latin1_General_CP1_CI_AS"
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT SERVERPROPERTY('Collation')")
                r = cur.fetchone()
                if r:
                    collate = str(r[0])
                cur.close()
            except Exception:
                pass

        return ConfigurationFacts(
            charset=CharsetFacts(server_encoding="CP1252"),
            collation=CollationFacts(default_collation=collate),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=1000),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        ags = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT name FROM sys.availability_groups")
                for r in cur.fetchall():
                    ags.append(str(r[0]))
                cur.close()
            except Exception:
                pass

        return TopologySnapshot(
            is_clustered=bool(ags),
            connected_node_role=NodeRole.PRIMARY if ags else NodeRole.UNKNOWN,
            nodes=(),
            availability_groups=tuple(ags),
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
                blocker_reasons=("MSSQL connection not established",),
            )
        is_cdc_db = False
        is_ct_db = False
        if hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT is_cdc_enabled FROM sys.databases WHERE name = DB_NAME()")
                r = cur.fetchone()
                if r:
                    is_cdc_db = bool(r[0])
                cur.execute("SELECT 1 FROM sys.change_tracking_databases WHERE database_id = DB_ID()")
                r = cur.fetchone()
                if r:
                    is_ct_db = True
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mssql CDC prereqs: {exc}")

        is_ready = is_cdc_db or is_ct_db
        blockers = []
        if not is_ready:
            blockers.append("Neither CDC nor Change Tracking is enabled on the database.")

        return CDCPrerequisiteSnapshot(
            is_cdc_ready=is_ready,
            mechanism=CDCMechanism.MSSQL_CDC if is_cdc_db else (CDCMechanism.MSSQL_CHANGE_TRACKING if is_ct_db else CDCMechanism.UNSUPPORTED),
            is_cdc_enabled_on_database=is_cdc_db,
            is_change_tracking_enabled_on_database=is_ct_db,
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
        if connection is None or not hasattr(connection, "cursor"):
            return DeterministicSampler.package_sample(table_name, schema_name, [], [])
        try:
            rows = []
            cols = []
            cur = connection.cursor()
            cur.execute(f"SELECT TOP {limit} * FROM [{schema_name}].[{table_name}]")
            cols = [d[0] for d in cur.description] if cur.description else []
            for r in cur.fetchall():
                rows.append(dict(zip(cols, r)))
            cur.close()
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling mssql table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))
