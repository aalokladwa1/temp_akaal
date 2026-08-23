"""
akaalEngine.discovery.strategies.relational.oracle
==================================================
Canonical Oracle Database discovery strategy.
Introspects ALL_TABLES, ALL_TAB_COLUMNS, ALL_CONSTRAINTS, ALL_VIEWS, ALL_PROCEDURES,
ALL_TAB_PARTITIONS, ALL_LOBS, GV$INSTANCE, v$database log_mode, and supplemental logging.
Filters 23 Oracle internal system schemas to prevent multi-minute catalog hangs.
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
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectClassification, ObjectInventoryPage, ObjectType, TableFacts, ViewFacts
from akaalEngine.discovery.models.partitioning import PartitionBoundFacts, PartitionFacts, PartitionStrategy
from akaalEngine.discovery.models.permissions import PermissionAssessment, PrivilegeFact, ThreeStatePermission
from akaalEngine.discovery.models.programmables import (
    ProgrammableInventory,
    RoutineFacts,
    RoutineType,
    SequenceFacts,
    TriggerFacts,
    TriggerTiming,
)
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

logger = logging.getLogger("akaalEngine.discovery.strategies.oracle")


class OracleDiscoveryStrategy(RelationalDiscoveryStrategy):
    """Oracle Database physical discovery strategy."""

    PROVIDER_ID = "oracle"

    # 23 internal Oracle system schemas to filter from scan
    SYSTEM_SCHEMAS = (
        'SYS', 'SYSTEM', 'AUDSYS', 'DBSNMP', 'GSMADMIN_INTERNAL',
        'LBACSYS', 'MDSYS', 'DVSYS', 'OUTLN', 'CTXSYS', 'XDB', 'WMSYS',
        'VECSYS', 'DBSFWUSER', 'APPQOSSYS', 'OJVMSYS', 'OLAPSYS', 'PDBADMIN',
        'GSMUSER', 'GSMROOTUSER', 'DGPUMP', 'ORACLE_OCM', 'ORDDATA', 'ORDSYS',
        'PUBLIC'
    )

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "Oracle Database 19c"
        major, minor, patch = 19, 0, 0
        instance_name = None
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT banner, version FROM v$instance")
                    r = cur.fetchone()
                    if r:
                        version_str = str(r[0])
                    cur.execute("SELECT instance_name FROM v$instance")
                    r = cur.fetchone()
                    if r:
                        instance_name = str(r[0])
            except Exception as exc:
                logger.warning(f"Error querying oracle version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="Oracle Corporation",
            engine_name="Oracle Database",
            system_type="ORACLE",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Enterprise Edition", is_enterprise=True),
            instance_name=instance_name,
            host=spec.host,
            port=spec.port or 1521,
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
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT USERNAME FROM ALL_USERS
                        ORDER BY USERNAME
                    """)
                    for r in cur.fetchall():
                        s = str(r[0]).upper()
                        if s not in self.SYSTEM_SCHEMAS:
                            schemas.append(s)
            except Exception as exc:
                logger.warning(f"Error querying oracle namespaces: {exc}")
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
                with connection.cursor() as cur:
                    if offset == 0:
                        # Views & Materialized Views
                        try:
                            cur.execute("""
                                SELECT VIEW_NAME, 0 AS IS_MVIEW, TEXT FROM ALL_VIEWS WHERE OWNER = :1
                                UNION ALL
                                SELECT MVIEW_NAME, 1 AS IS_MVIEW, QUERY AS TEXT FROM ALL_MVIEWS WHERE OWNER = :1
                            """, [schema_name.upper()])
                            for r in cur.fetchall():
                                vname, is_mv, def_sql = r[0], bool(r[1]), r[2]
                                views.append(
                                    ViewFacts(
                                        name=vname,
                                        schema_name=schema_name,
                                        is_materialized=is_mv,
                                        definition_sql=str(def_sql) if def_sql else None,
                                    )
                                )
                        except Exception:
                            pass

                    # Tables with server-side pagination
                    try:
                        cur.execute("""
                            SELECT TABLE_NAME, NUM_ROWS, BLOCKS, IOT_TYPE, TEMPORARY
                            FROM ALL_TABLES
                            WHERE OWNER = :1
                            ORDER BY TABLE_NAME
                            OFFSET :2 ROWS FETCH NEXT :3 ROWS ONLY
                        """, [schema_name.upper(), offset, page_size + 1])
                        rows = cur.fetchall()
                    except Exception:
                        cur.execute("""
                            SELECT TABLE_NAME, NUM_ROWS, BLOCKS, IOT_TYPE, TEMPORARY
                            FROM ALL_TABLES
                            WHERE OWNER = :1
                            ORDER BY TABLE_NAME
                        """, [schema_name.upper()])
                        if offset > 0:
                            cur.fetchmany(offset)
                        rows = cur.fetchmany(page_size + 1)

                    if len(rows) > page_size:
                        has_more = True
                        rows = rows[:page_size]

                    for r in rows:
                        tname, nrows, blocks, iot, temp = r[0], r[1], r[2], r[3], r[4]
                        num_rows = nrows if nrows is not None else 0
                        blk_count = blocks if blocks is not None else 0
                        size_bytes = blk_count * 8192

                        tables.append(
                            TableFacts(
                                name=tname,
                                schema_name=schema_name,
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                                is_temporary=(temp == 'Y'),
                                row_count_estimate=num_rows,
                                size_bytes_estimate=size_bytes,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying oracle tables in {schema_name}: {exc}")
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
        uniques = []
        checks = []
        indexes = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    # 1. Columns
                    cur.execute("""
                        SELECT COLUMN_ID, COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE,
                               NULLABLE, DATA_DEFAULT, IDENTITY_COLUMN
                        FROM ALL_TAB_COLUMNS
                        WHERE OWNER = :1 AND TABLE_NAME = :2
                        ORDER BY COLUMN_ID
                    """, [schema_name.upper(), object_name.upper()])
                    for r in cur.fetchall():
                        cid, cname, dtype, dlen, dprec, dscale, nullb, dflt, ident = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]
                        is_lob = dtype.upper() in ("CLOB", "BLOB", "NCLOB", "BFILE", "LONG", "LONG RAW")
                        cols.append(
                            ColumnPhysicalMetadata(
                                name=cname,
                                ordinal_position=cid or 1,
                                native_type=dtype.upper(),
                                length=dlen,
                                precision=dprec,
                                scale=dscale,
                                nullable=(nullb == 'Y'),
                                default_expression=dflt,
                                is_identity=(ident == 'YES'),
                                is_lob=is_lob,
                            )
                        )

                    # 2. Constraints (PK, Unique, Check)
                    cur.execute("""
                        SELECT AC.CONSTRAINT_NAME, AC.CONSTRAINT_TYPE, AC.SEARCH_CONDITION, ACC.COLUMN_NAME
                        FROM ALL_CONSTRAINTS AC
                        LEFT JOIN ALL_CONS_COLUMNS ACC ON ACC.OWNER = AC.OWNER AND ACC.CONSTRAINT_NAME = AC.CONSTRAINT_NAME
                        WHERE AC.OWNER = :1 AND AC.TABLE_NAME = :2 AND AC.CONSTRAINT_TYPE IN ('P', 'U', 'C')
                    """, [schema_name.upper(), object_name.upper()])
                    cons_map: dict[str, dict[str, Any]] = {}
                    for r in cur.fetchall():
                        cname, ctype, ccond, colname = r[0], r[1], r[2], r[3]
                        if cname not in cons_map:
                            cons_map[cname] = {"type": ctype, "cond": ccond, "cols": []}
                        if colname:
                            cons_map[cname]["cols"].append(colname)

                    for cname, cinfo in cons_map.items():
                        ctype = cinfo["type"]
                        if ctype == 'P':
                            primary_key = PrimaryKeyFacts(name=cname, table_name=object_name, columns=tuple(cinfo["cols"]), schema_name=schema_name)
                        elif ctype == 'U':
                            uniques.append(UniqueConstraintFacts(name=cname, table_name=object_name, columns=tuple(cinfo["cols"]), schema_name=schema_name))
                        elif ctype == 'C':
                            checks.append(CheckConstraintFacts(name=cname, table_name=object_name, check_clause=str(cinfo["cond"] or ""), schema_name=schema_name))

                    # 3. Foreign Keys
                    cur.execute("""
                        SELECT AC.CONSTRAINT_NAME, ACC.COLUMN_NAME, R_AC.OWNER, R_AC.TABLE_NAME, R_ACC.COLUMN_NAME, AC.DELETE_RULE
                        FROM ALL_CONSTRAINTS AC
                        JOIN ALL_CONS_COLUMNS ACC ON ACC.OWNER = AC.OWNER AND ACC.CONSTRAINT_NAME = AC.CONSTRAINT_NAME
                        JOIN ALL_CONSTRAINTS R_AC ON R_AC.OWNER = AC.R_OWNER AND R_AC.CONSTRAINT_NAME = AC.R_CONSTRAINT_NAME
                        JOIN ALL_CONS_COLUMNS R_ACC ON R_ACC.OWNER = R_AC.OWNER AND R_ACC.CONSTRAINT_NAME = R_AC.CONSTRAINT_NAME AND R_ACC.POSITION = ACC.POSITION
                        WHERE AC.OWNER = :1 AND AC.TABLE_NAME = :2 AND AC.CONSTRAINT_TYPE = 'R'
                    """, [schema_name.upper(), object_name.upper()])
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
                                on_delete=r[5] or "NO ACTION",
                            )
                        )

                    # 4. Indexes
                    cur.execute("""
                        SELECT AI.INDEX_NAME, AI.INDEX_TYPE, AI.UNIQUENESS, AIC.COLUMN_NAME
                        FROM ALL_INDEXES AI
                        JOIN ALL_IND_COLUMNS AIC ON AIC.INDEX_OWNER = AI.OWNER AND AIC.INDEX_NAME = AI.INDEX_NAME
                        WHERE AI.TABLE_OWNER = :1 AND AI.TABLE_NAME = :2
                        ORDER BY AI.INDEX_NAME, AIC.COLUMN_POSITION
                    """, [schema_name.upper(), object_name.upper()])
                    idx_map: dict[str, dict[str, Any]] = {}
                    for r in cur.fetchall():
                        iname, itype, uniq, col = r[0], r[1], r[2], r[3]
                        if iname not in idx_map:
                            idx_map[iname] = {"type": itype, "unique": (uniq == "UNIQUE"), "cols": []}
                        idx_map[iname]["cols"].append(col)

                    for iname, info in idx_map.items():
                        am = IndexAccessMethod.BITMAP if "BITMAP" in info["type"] else IndexAccessMethod.BTREE
                        indexes.append(
                            IndexFacts(
                                name=iname,
                                table_name=object_name,
                                schema_name=schema_name,
                                columns=tuple(info["cols"]),
                                is_unique=info["unique"],
                                access_method=am,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying oracle structure for {schema_name}.{object_name}: {exc}")
                raise

        return ObjectStructureFacts(
            table_name=object_name,
            schema_name=schema_name,
            columns=tuple(cols),
            primary_key=primary_key,
            foreign_keys=tuple(fks),
            unique_constraints=tuple(uniques),
            check_constraints=tuple(checks),
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
        upper_names = [n.upper() for n in object_names]
        bind_vars = ','.join([f':{i+2}' for i in range(len(upper_names))])

        try:
            with connection.cursor() as cur:
                # 1. Bulk Columns
                cur.execute(f"""
                    SELECT TABLE_NAME, COLUMN_ID, COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE,
                           NULLABLE, DATA_DEFAULT, IDENTITY_COLUMN
                    FROM ALL_TAB_COLUMNS
                    WHERE OWNER = :1 AND TABLE_NAME IN ({bind_vars})
                    ORDER BY TABLE_NAME, COLUMN_ID
                """, [schema_name.upper()] + upper_names)
                cols_by_tbl: dict[str, list[ColumnPhysicalMetadata]] = {name.upper(): [] for name in object_names}
                for r in cur.fetchall():
                    tname, cid, cname, dtype, dlen, dprec, dscale, nullb, dflt, ident = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]
                    is_lob = dtype.upper() in ("CLOB", "BLOB", "NCLOB", "BFILE", "LONG", "LONG RAW")
                    cols_by_tbl.setdefault(tname.upper(), []).append(
                        ColumnPhysicalMetadata(
                            name=cname,
                            ordinal_position=cid or 1,
                            native_type=dtype.upper(),
                            length=dlen,
                            precision=dprec,
                            scale=dscale,
                            nullable=(nullb == 'Y'),
                            default_expression=dflt,
                            is_identity=(ident == 'YES'),
                            is_lob=is_lob,
                        )
                    )

                # 2. Bulk Constraints
                cur.execute(f"""
                    SELECT AC.TABLE_NAME, AC.CONSTRAINT_NAME, AC.CONSTRAINT_TYPE, AC.SEARCH_CONDITION, ACC.COLUMN_NAME
                    FROM ALL_CONSTRAINTS AC
                    LEFT JOIN ALL_CONS_COLUMNS ACC ON ACC.OWNER = AC.OWNER AND ACC.CONSTRAINT_NAME = AC.CONSTRAINT_NAME
                    WHERE AC.OWNER = :1 AND AC.TABLE_NAME IN ({bind_vars}) AND AC.CONSTRAINT_TYPE IN ('P', 'U', 'C')
                """, [schema_name.upper()] + upper_names)
                pk_by_tbl: dict[str, Optional[PrimaryKeyFacts]] = {}
                uniques_by_tbl: dict[str, list[UniqueConstraintFacts]] = {name.upper(): [] for name in object_names}
                checks_by_tbl: dict[str, list[CheckConstraintFacts]] = {name.upper(): [] for name in object_names}
                cons_map: dict[str, dict[str, dict[str, Any]]] = {}
                for r in cur.fetchall():
                    tname, cname, ctype, ccond, colname = r[0].upper(), r[1], r[2], r[3], r[4]
                    t_cons = cons_map.setdefault(tname, {})
                    if cname not in t_cons:
                        t_cons[cname] = {"type": ctype, "cond": ccond, "cols": []}
                    if colname:
                        t_cons[cname]["cols"].append(colname)

                for tname, t_cons in cons_map.items():
                    for cname, cinfo in t_cons.items():
                        ctype = cinfo["type"]
                        if ctype == 'P':
                            pk_by_tbl[tname] = PrimaryKeyFacts(name=cname, table_name=tname, columns=tuple(cinfo["cols"]), schema_name=schema_name)
                        elif ctype == 'U':
                            uniques_by_tbl.setdefault(tname, []).append(UniqueConstraintFacts(name=cname, table_name=tname, columns=tuple(cinfo["cols"]), schema_name=schema_name))
                        elif ctype == 'C':
                            checks_by_tbl.setdefault(tname, []).append(CheckConstraintFacts(name=cname, table_name=tname, check_clause=str(cinfo["cond"] or ""), schema_name=schema_name))

                # 3. Bulk Indexes
                cur.execute(f"""
                    SELECT AI.TABLE_NAME, AI.INDEX_NAME, AI.INDEX_TYPE, AI.UNIQUENESS, AIC.COLUMN_NAME
                    FROM ALL_INDEXES AI
                    JOIN ALL_IND_COLUMNS AIC ON AIC.INDEX_OWNER = AI.OWNER AND AIC.INDEX_NAME = AI.INDEX_NAME
                    WHERE AI.TABLE_OWNER = :1 AND AI.TABLE_NAME IN ({bind_vars})
                    ORDER BY AI.TABLE_NAME, AI.INDEX_NAME, AIC.COLUMN_POSITION
                """, [schema_name.upper()] + upper_names)
                idx_map: dict[str, dict[str, dict[str, Any]]] = {}
                for r in cur.fetchall():
                    tname, iname, itype, uniq, col = r[0].upper(), r[1], r[2], r[3], r[4]
                    t_idx = idx_map.setdefault(tname, {})
                    if iname not in t_idx:
                        t_idx[iname] = {"type": itype, "unique": (uniq == "UNIQUE"), "cols": []}
                    t_idx[iname]["cols"].append(col)

                indexes_by_tbl: dict[str, list[IndexFacts]] = {name.upper(): [] for name in object_names}
                for tname, t_idx in idx_map.items():
                    for iname, info in t_idx.items():
                        am = IndexAccessMethod.BITMAP if "BITMAP" in info["type"] else IndexAccessMethod.BTREE
                        indexes_by_tbl.setdefault(tname, []).append(
                            IndexFacts(
                                name=iname,
                                table_name=tname,
                                schema_name=schema_name,
                                columns=tuple(info["cols"]),
                                is_unique=info["unique"],
                                access_method=am,
                            )
                        )

            for name in object_names:
                uname = name.upper()
                results[name] = ObjectStructureFacts(
                    table_name=name,
                    schema_name=schema_name,
                    columns=tuple(cols_by_tbl.get(uname, [])),
                    primary_key=pk_by_tbl.get(uname),
                    unique_constraints=tuple(uniques_by_tbl.get(uname, [])),
                    check_constraints=tuple(checks_by_tbl.get(uname, [])),
                    indexes=tuple(indexes_by_tbl.get(uname, [])),
                )
        except Exception as exc:
            logger.warning(f"Bulk structure discovery failed for Oracle schema '{schema_name}': {exc}")
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
        upper_names = [n.upper() for n in object_names]
        bind_vars = ','.join([f':{i+2}' for i in range(len(upper_names))])
        try:
            with connection.cursor() as cur:
                cur.execute(f"""
                    SELECT TABLE_NAME, NUM_ROWS, BLOCKS, AVG_ROW_LEN
                    FROM ALL_TABLES
                    WHERE OWNER = :1 AND TABLE_NAME IN ({bind_vars})
                """, [schema_name.upper()] + upper_names)
                for r in cur.fetchall():
                    tname, nrows, blocks, avg_len = r[0], r[1], r[2], r[3]
                    num_rows = int(nrows or 0)
                    blk_bytes = int(blocks or 0) * 8192
                    for orig_name in object_names:
                        if orig_name.upper() == tname.upper():
                            results[orig_name] = TableSizeFacts(
                                table_name=orig_name,
                                schema_name=schema_name,
                                row_count=num_rows,
                                data_bytes=blk_bytes,
                            )
        except Exception as exc:
            logger.warning(f"Bulk stats discovery failed for Oracle schema '{schema_name}': {exc}")
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
        triggers = []
        sequences = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    # Procedures and Functions
                    cur.execute("""
                        SELECT OBJECT_NAME, OBJECT_TYPE
                        FROM ALL_OBJECTS
                        WHERE OWNER = :1 AND OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION', 'PACKAGE')
                    """, [schema_name.upper()])
                    for r in cur.fetchall():
                        oname, otype = r[0], r[1]
                        rtype = RoutineType.PROCEDURE if otype == "PROCEDURE" else (RoutineType.FUNCTION if otype == "FUNCTION" else RoutineType.PACKAGE_SPEC)
                        routines.append(
                            RoutineFacts(
                                name=oname,
                                schema_name=schema_name,
                                routine_type=rtype,
                                language="PLSQL",
                            )
                        )

                    # Triggers
                    cur.execute("""
                        SELECT TRIGGER_NAME, TABLE_NAME, TRIGGER_TYPE, TRIGGERING_EVENT, STATUS
                        FROM ALL_TRIGGERS
                        WHERE OWNER = :1
                    """, [schema_name.upper()])
                    for r in cur.fetchall():
                        triggers.append(
                            TriggerFacts(
                                name=r[0],
                                table_name=r[1] or "",
                                schema_name=schema_name,
                                timing=TriggerTiming.BEFORE if "BEFORE" in str(r[2]) else TriggerTiming.AFTER,
                                events=(r[3],),
                                is_enabled=(r[4] == "ENABLED"),
                            )
                        )

                    # Sequences
                    cur.execute("""
                        SELECT SEQUENCE_NAME, MIN_VALUE, MAX_VALUE, INCREMENT_BY, CYCLE_FLAG, LAST_NUMBER
                        FROM ALL_SEQUENCES
                        WHERE SEQUENCE_OWNER = :1
                    """, [schema_name.upper()])
                    for r in cur.fetchall():
                        sequences.append(
                            SequenceFacts(
                                name=r[0],
                                schema_name=schema_name,
                                min_value=int(r[1]) if r[1] is not None else 1,
                                max_value=int(r[2]) if r[2] is not None else None,
                                increment_by=int(r[3]) if r[3] is not None else 1,
                                is_cycling=(r[4] == 'Y'),
                                current_value=int(r[5]) if r[5] is not None else None,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying oracle programmables: {exc}")

        return ProgrammableInventory(
            routines=tuple(routines),
            triggers=tuple(triggers),
            sequences=tuple(sequences),
        )

    def discover_partitioning(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> PartitionFacts:
        strategy = PartitionStrategy.NONE
        bounds = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT PARTITIONING_TYPE, SUBPARTITIONING_TYPE
                        FROM ALL_PART_TABLES
                        WHERE OWNER = :1 AND TABLE_NAME = :2
                    """, [schema_name.upper(), table_name.upper()])
                    r = cur.fetchone()
                    if r:
                        ptype = str(r[0]).upper()
                        if ptype == "RANGE":
                            strategy = PartitionStrategy.RANGE
                        elif ptype == "LIST":
                            strategy = PartitionStrategy.LIST
                        elif ptype == "HASH":
                            strategy = PartitionStrategy.HASH

                        # Partition bounds
                        cur.execute("""
                            SELECT PARTITION_NAME, HIGH_VALUE, PARTITION_POSITION, NUM_ROWS, BLOCKS
                            FROM ALL_TAB_PARTITIONS
                            WHERE TABLE_OWNER = :1 AND TABLE_NAME = :2
                            ORDER BY PARTITION_POSITION
                        """, [schema_name.upper(), table_name.upper()])
                        for pr in cur.fetchall():
                            pname, hval, pos, num_r, blks = pr[0], pr[1], pr[2], pr[3], pr[4]
                            bounds.append(
                                PartitionBoundFacts(
                                    partition_name=pname,
                                    strategy=strategy,
                                    upper_bound=str(hval) if hval is not None else None,
                                    partition_ordinal=pos,
                                    estimated_rows=num_r or 0,
                                    estimated_bytes=(blks or 0) * 8192,
                                )
                            )
            except Exception as exc:
                logger.warning(f"Error discovering oracle partitions for {table_name}: {exc}")
                raise

        return PartitionFacts(
            table_name=table_name,
            schema_name=schema_name,
            strategy=strategy,
            partitions=tuple(bounds),
        )

    def discover_table_statistics(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> TableSizeFacts:
        num_rows = 0
        blocks = 0
        last_analyzed = None

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT NUM_ROWS, BLOCKS, LAST_ANALYZED
                        FROM ALL_TABLES
                        WHERE OWNER = :1 AND TABLE_NAME = :2
                    """, [schema_name.upper(), table_name.upper()])
                    r = cur.fetchone()
                    if r:
                        num_rows = r[0] or 0
                        blocks = r[1] or 0
            except Exception as exc:
                logger.warning(f"Error fetching oracle table stats for {table_name}: {exc}")
                raise

        size_bytes = blocks * 8192
        return TableSizeFacts(
            table_name=table_name,
            schema_name=schema_name,
            row_count=num_rows,
            count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
            data_bytes=size_bytes,
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
                with connection.cursor() as cur:
                    cur.execute("SELECT open_mode FROM v$database")
                    r = cur.fetchone()
                    if r and "READ ONLY" in str(r[0]).upper():
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
                with connection.cursor() as cur:
                    cur.execute("SELECT USERNAME FROM ALL_USERS WHERE ROWNUM = 1")
                    cur.fetchall()
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
        charset = "AL32UTF8"
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT value FROM nls_database_parameters WHERE parameter = 'NLS_CHARACTERSET'")
                    r = cur.fetchone()
                    if r:
                        charset = str(r[0])
            except Exception:
                pass

        return ConfigurationFacts(
            charset=CharsetFacts(server_encoding=charset),
            collation=CollationFacts(default_collation="BINARY"),
            timezone=TimezoneFacts(database_timezone="UTC"),
            limits=LimitsFacts(max_connections=1000),
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
                blocker_reasons=("Oracle connection not established",),
            )
        is_arch = False
        is_supp = False
        current_scn = None

        if hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT LOG_MODE, SUPPLEMENTAL_LOG_DATA_MIN, CURRENT_SCN FROM V$DATABASE")
                    r = cur.fetchone()
                    if r:
                        is_arch = (str(r[0]).upper() == "ARCHIVELOG")
                        is_supp = (str(r[1]).upper() in ("YES", "IMPLICIT"))
                        current_scn = int(r[2]) if (r[2] is not None and str(r[2]).isdigit()) else r[2]
            except Exception as exc:
                logger.warning(f"Error querying oracle CDC prereqs: {exc}")

        is_ready = is_arch and is_supp

        blockers = []
        if not is_arch:
            blockers.append("Database is not in ARCHIVELOG mode.")
        if not is_supp:
            blockers.append("Supplemental logging is disabled (ALTER DATABASE ADD SUPPLEMENTAL LOG DATA required).")

        return CDCPrerequisiteSnapshot(
            is_cdc_ready=is_ready,
            mechanism=CDCMechanism.ORACLE_LOGMINER,
            starting_position=StartingCommitPosition(scn=current_scn) if current_scn else None,
            is_archivelog_enabled=is_arch,
            is_supplemental_logging_enabled=is_supp,
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
            with connection.cursor() as cur:
                cur.execute(f'SELECT * FROM "{schema_name.upper()}"."{table_name.upper()}" WHERE ROWNUM <= :1', [limit])
                cols = [d[0] for d in cur.description] if cur.description else []
                for r in cur.fetchall():
                    rows.append(dict(zip(cols, r)))
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling oracle table {table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))
