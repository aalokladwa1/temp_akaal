"""
akaalEngine.discovery.strategies.relational.mysql
================================================
Canonical MySQL discovery strategy.
Introspects information_schema tables, columns, constraints, statistics,
SHOW MASTER STATUS, and binlog/GTID settings.
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
from akaalEngine.discovery.models.programmables import ProgrammableInventory, RoutineFacts, RoutineType, TriggerFacts
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

logger = logging.getLogger("akaalEngine.discovery.strategies.mysql")


class MySQLDiscoveryStrategy(RelationalDiscoveryStrategy):
    """MySQL physical discovery strategy."""

    PROVIDER_ID = "mysql"

    SYSTEM_SCHEMAS = ('information_schema', 'mysql', 'performance_schema', 'sys')

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "8.0.32"
        major, minor, patch = 8, 0, 32
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SELECT VERSION()")
                r = cur.fetchone()
                if r:
                    version_str = str(r[0])
                    clean_v = version_str.split("-")[0]
                    parts = clean_v.split(".")
                    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 8
                    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mysql version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Oracle / MySQL Community",
            engine_name="MySQL Server",
            system_type="MYSQL",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Community Server", is_enterprise=False),
            host=spec.host,
            port=spec.port or 3306,
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
                cur.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME")
                for r in cur.fetchall():
                    s = str(r[0])
                    if s.lower() not in self.SYSTEM_SCHEMAS:
                        schemas.append(s)
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mysql schemas: {exc}")
                raise

        return NamespaceInventory(
            schemas=tuple(schemas),
            system_schemas=self.SYSTEM_SCHEMAS,
            default_schema=schemas[0] if schemas else None,
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
                cur.execute("""
                    SELECT TABLE_NAME, TABLE_TYPE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                    LIMIT %s OFFSET %s
                """, (schema_name, page_size + 1, offset))
                rows = cur.fetchall()
                if len(rows) > page_size:
                    has_more = True
                    rows = rows[:page_size]

                for r in rows:
                    tname, ttype, nrows, dlen, ilen = r[0], r[1], r[2], r[3], r[4]
                    if "VIEW" in str(ttype).upper():
                        views.append(
                            ViewFacts(
                                name=tname,
                                schema_name=schema_name,
                                is_materialized=False,
                            )
                        )
                    else:
                        tot_bytes = (dlen or 0) + (ilen or 0)
                        tables.append(
                            TableFacts(
                                name=tname,
                                schema_name=schema_name,
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                                row_count_estimate=nrows or 0,
                                size_bytes_estimate=tot_bytes,
                            )
                        )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mysql tables in {schema_name}: {exc}")
                raise

        next_cursor = None
        if has_more:
            next_cursor = DiscoveryCursor(offset=offset + len(tables) + len(views), generation_token=f"{schema_name}_{offset}").encode()

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
                    SELECT ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                           NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (schema_name, object_name))
                for r in cur.fetchall():
                    pos, cname, dtype, clen, prec, scale, nullb, dflt, extra = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]
                    is_auto = "auto_increment" in str(extra).lower()
                    is_lob = any(t in str(dtype).lower() for t in ("blob", "text", "json"))
                    cols.append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=pos,
                            native_type=str(dtype).upper(),
                            length=clen,
                            precision=prec,
                            scale=scale,
                            nullable=(str(nullb).upper() == "YES"),
                            default_expression=str(dflt) if dflt is not None else None,
                            is_identity=is_auto,
                            is_lob=is_lob,
                        )
                    )

                # Primary Key & Indexes
                cur.execute("""
                    SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE, INDEX_TYPE
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """, (schema_name, object_name))
                idx_map: dict[str, dict[str, Any]] = {}
                for r in cur.fetchall():
                    iname, col, non_u, itype = r[0], r[1], r[2], r[3]
                    if iname not in idx_map:
                        idx_map[iname] = {"cols": [], "unique": (non_u == 0), "type": itype}
                    idx_map[iname]["cols"].append(col)

                for iname, info in idx_map.items():
                    if iname == "PRIMARY":
                        primary_key = PrimaryKeyFacts(name="PRIMARY", table_name=object_name, columns=tuple(info["cols"]), schema_name=schema_name)
                    else:
                        indexes.append(
                            IndexFacts(
                                name=iname,
                                table_name=object_name,
                                schema_name=schema_name,
                                columns=tuple(info["cols"]),
                                is_unique=info["unique"],
                                access_method=IndexAccessMethod.BTREE,
                            )
                        )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mysql structure for {schema_name}.{object_name}: {exc}")
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
        format_strings = ','.join(['%s'] * len(names_list))

        try:
            cur = connection.cursor()
            # 1. Bulk Columns
            cur.execute(f"""
                SELECT TABLE_NAME, ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                       NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({format_strings})
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """, [schema_name] + names_list)
            cols_by_tbl: dict[str, list[ColumnPhysicalMetadata]] = {name: [] for name in object_names}
            for r in cur.fetchall():
                tname, pos, cname, dtype, clen, prec, scale, nullb, dflt, extra = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]
                is_auto = "auto_increment" in str(extra).lower()
                is_lob = any(t in str(dtype).lower() for t in ("blob", "text", "json"))
                cols_by_tbl.setdefault(tname, []).append(
                    ColumnPhysicalMetadata(
                        name=cname,
                        ordinal_position=pos,
                        native_type=str(dtype).upper(),
                        length=clen,
                        precision=prec,
                        scale=scale,
                        nullable=(str(nullb).upper() == "YES"),
                        default_expression=str(dflt) if dflt is not None else None,
                        is_identity=is_auto,
                        is_lob=is_lob,
                    )
                )

            # 2. Bulk Indexes & Primary Keys
            cur.execute(f"""
                SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, NON_UNIQUE, INDEX_TYPE
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({format_strings})
                ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
            """, [schema_name] + names_list)
            idx_map: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in object_names}
            for r in cur.fetchall():
                tname, iname, col, non_u, itype = r[0], r[1], r[2], r[3], r[4]
                t_idx = idx_map.setdefault(tname, {})
                if iname not in t_idx:
                    t_idx[iname] = {"cols": [], "unique": (non_u == 0), "type": itype}
                t_idx[iname]["cols"].append(col)

            pk_by_tbl: dict[str, Optional[PrimaryKeyFacts]] = {}
            indexes_by_tbl: dict[str, list[IndexFacts]] = {name: [] for name in object_names}

            for tname, t_idx in idx_map.items():
                for iname, info in t_idx.items():
                    if iname == "PRIMARY":
                        pk_by_tbl[tname] = PrimaryKeyFacts(name="PRIMARY", table_name=tname, columns=tuple(info["cols"]), schema_name=schema_name)
                    else:
                        indexes_by_tbl.setdefault(tname, []).append(
                            IndexFacts(
                                name=iname,
                                table_name=tname,
                                schema_name=schema_name,
                                columns=tuple(info["cols"]),
                                is_unique=info["unique"],
                                access_method=IndexAccessMethod.BTREE,
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
            logger.warning(f"Bulk structure discovery failed for MySQL schema '{schema_name}': {exc}")
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

        results: dict[str, TableSizeFacts] = {}
        names_list = list(object_names)
        format_strings = ','.join(['%s'] * len(names_list))
        try:
            cur = connection.cursor()
            cur.execute(f"""
                SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({format_strings})
            """, [schema_name] + names_list)
            for r in cur.fetchall():
                tname, nrows, dlen, ilen = r[0], r[1], r[2], r[3]
                results[tname] = TableSizeFacts(
                    table_name=tname,
                    schema_name=schema_name,
                    row_count=nrows or 0,
                    data_bytes=dlen or 0,
                    index_bytes=ilen or 0,
                )
            cur.close()
        except Exception as exc:
            logger.warning(f"Bulk stats discovery failed for MySQL schema '{schema_name}': {exc}")
            raise

        for name in object_names:
            if name not in results:
                results[name] = TableSizeFacts(table_name=name, schema_name=schema_name, row_count=0)

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
                    FROM information_schema.ROUTINES
                    WHERE ROUTINE_SCHEMA = %s
                """, (schema_name,))
                for r in cur.fetchall():
                    rname, rtype, rdef = r[0], r[1], r[2]
                    routines.append(
                        RoutineFacts(
                            name=rname,
                            schema_name=schema_name,
                            routine_type=RoutineType.PROCEDURE if rtype == "PROCEDURE" else RoutineType.FUNCTION,
                            definition_sql=rdef,
                        )
                    )
                cur.close()
            except Exception as exc:
                logger.warning(f"Error discovering mysql routines: {exc}")

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
        dlen = 0
        ilen = 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("""
                    SELECT TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (schema_name, table_name))
                r = cur.fetchone()
                if r:
                    rows = r[0] or 0
                    dlen = r[1] or 0
                    ilen = r[2] or 0
                cur.close()
            except Exception as exc:
                logger.warning(f"Error fetching stats for {table_name}: {exc}")
                raise

        return TableSizeFacts(
            table_name=table_name,
            schema_name=schema_name,
            row_count=rows,
            count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
            data_bytes=dlen,
            index_bytes=ilen,
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
                cur.execute("SHOW VARIABLES LIKE 'read_only'")
                r = cur.fetchone()
                cur.close()
                if r and str(r[1]).upper() in ("ON", "1"):
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
                cur.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA LIMIT 1")
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
        charset = "utf8mb4"
        max_conn = 151
        if connection is not None and hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SHOW VARIABLES LIKE 'character_set_server'")
                r = cur.fetchone()
                if r:
                    charset = str(r[1])
                cur.execute("SHOW VARIABLES LIKE 'max_connections'")
                r = cur.fetchone()
                if r:
                    max_conn = int(r[1])
                cur.close()
            except Exception:
                pass

        return ConfigurationFacts(
            charset=CharsetFacts(server_encoding=charset),
            collation=CollationFacts(default_collation="utf8mb4_0900_ai_ci"),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=max_conn),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        return TopologySnapshot(
            is_clustered=False,
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
                blocker_reasons=("MySQL connection not established",),
            )
        log_bin = "OFF"
        binlog_format = "ROW"
        gtid_mode = "OFF"
        binlog_file = None
        binlog_pos = None

        if hasattr(connection, "cursor"):
            try:
                cur = connection.cursor()
                cur.execute("SHOW VARIABLES LIKE 'log_bin'")
                r = cur.fetchone()
                if r:
                    log_bin = str(r[1]).upper()

                cur.execute("SHOW VARIABLES LIKE 'binlog_format'")
                r = cur.fetchone()
                if r:
                    binlog_format = str(r[1]).upper()

                cur.execute("SHOW VARIABLES LIKE 'gtid_mode'")
                r = cur.fetchone()
                if r:
                    gtid_mode = str(r[1]).upper()

                cur.execute("SHOW MASTER STATUS")
                r = cur.fetchone()
                if r:
                    binlog_file = str(r[0])
                    binlog_pos = int(r[1])
                cur.close()
            except Exception as exc:
                logger.warning(f"Error querying mysql CDC prereqs: {exc}")

        is_bin_on = (log_bin == "ON")
        is_row = (binlog_format == "ROW")
        is_ready = is_bin_on and is_row

        blockers = []
        if not is_bin_on:
            blockers.append("log_bin is OFF (binary logging required for CDC).")
        if not is_row:
            blockers.append(f"binlog_format is '{binlog_format}' (must be 'ROW').")

        return CDCPrerequisiteSnapshot(
            is_cdc_ready=is_ready,
            mechanism=CDCMechanism.MYSQL_BINLOG,
            starting_position=StartingCommitPosition(binlog_file=binlog_file, binlog_position=binlog_pos) if binlog_file else None,
            is_binlog_enabled=is_bin_on,
            is_binlog_format_row=is_row,
            is_gtid_enabled=(gtid_mode == "ON"),
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
            cur.execute(f"SELECT * FROM `{schema_name}`.`{table_name}` LIMIT {limit}")
            cols = [d[0] for d in cur.description] if cur.description else []
            for r in cur.fetchall():
                rows.append(dict(zip(cols, r)))
            cur.close()
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling mysql table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))
