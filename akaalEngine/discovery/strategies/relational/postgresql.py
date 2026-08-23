"""
akaalEngine.discovery.strategies.relational.postgresql
======================================================
Canonical PostgreSQL discovery strategy.
Introspects pg_namespace, pg_class, pg_attribute, pg_constraint, pg_index, pg_stats,
pg_stat_replication, pg_replication_slots, and wal_level.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.core.paginator import CatalogPaginator, DiscoveryCursor
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
    RoutineParameterFacts,
    RoutineType,
    SequenceFacts,
    TriggerFacts,
    TriggerTiming,
    UDTFacts,
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

logger = logging.getLogger("akaalEngine.discovery.strategies.postgresql")


class PostgresDiscoveryStrategy(RelationalDiscoveryStrategy):
    """PostgreSQL physical discovery strategy."""

    PROVIDER_ID = "postgresql"

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        version_str = "PostgreSQL"
        major, minor, patch = 15, 0, 0
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT version(), current_setting('server_version_num')")
                    row = cur.fetchone()
                    if row:
                        version_str = str(row[0])
                        ver_num = int(row[1])
                        major = ver_num // 10000
                        minor = (ver_num % 10000) // 100
                        patch = ver_num % 100
            except Exception as exc:
                logger.warning(f"Error fetching pg version: {exc}")

        return DiscoveredEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            vendor_name="PostgreSQL Global Development Group",
            engine_name="PostgreSQL",
            system_type="POSTGRESQL",
            version=ServerVersion(raw_version_string=version_str, major=major, minor=minor, patch=patch),
            edition=EngineEdition(edition_name="Community / Enterprise", is_enterprise=True),
            host=spec.host,
            port=spec.port or 5432,
            database_name=spec.database_name,
        )

    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        schemas = []
        system_schemas = []
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT nspname FROM pg_namespace 
                        ORDER BY nspname
                    """)
                    for row in cur.fetchall():
                        s = str(row[0])
                        if s.startswith("pg_") or s in ("information_schema", "pg_toast"):
                            system_schemas.append(s)
                        else:
                            schemas.append(s)
            except Exception as exc:
                logger.warning(f"Error discovering pg namespaces: {exc}")
                raise

        return NamespaceInventory(
            schemas=tuple(schemas),
            system_schemas=tuple(system_schemas),
            default_schema="public" if "public" in schemas else (schemas[0] if schemas else None),
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
                        cur.execute("""
                            SELECT c.relname, c.relkind
                            FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname = %s AND c.relkind IN ('v', 'm')
                            ORDER BY c.relname
                        """, (schema_name,))
                        for row in cur.fetchall():
                            views.append(
                                ViewFacts(
                                    name=str(row[0]),
                                    schema_name=schema_name,
                                    is_materialized=(row[1] == 'm'),
                                )
                            )

                    cur.execute("""
                        SELECT c.relname, c.relkind, c.relpersistence,
                               COALESCE(c.reltuples, 0)::bigint AS est_rows,
                               pg_total_relation_size(c.oid) AS total_bytes
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = %s 
                          AND c.relkind IN ('r', 'p', 'f')
                        ORDER BY c.relname
                        LIMIT %s OFFSET %s
                    """, (schema_name, page_size + 1, offset))
                    
                    rows = cur.fetchall()
                    if len(rows) > page_size:
                        has_more = True
                        rows = rows[:page_size]

                    for row in rows:
                        rname, rkind, rpersist, est_rows, tot_bytes = row[0], row[1], row[2], row[3], row[4]
                        is_unlogged = (rpersist == 'u')
                        is_temp = (rpersist == 't')
                        tables.append(
                            TableFacts(
                                name=rname,
                                schema_name=schema_name,
                                object_type=ObjectType.TABLE,
                                classification=ObjectClassification.USER,
                                is_unlogged=is_unlogged,
                                is_temporary=is_temp,
                                is_external=(rkind == 'f'),
                                row_count_estimate=max(0, int(est_rows)),
                                size_bytes_estimate=max(0, int(tot_bytes)),
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying pg tables in {schema_name}: {exc}")
                raise

        next_cursor = None
        if has_more:
            next_cursor = DiscoveryCursor(schema_index=0, offset=offset + len(tables)).encode()

        return ObjectInventoryPage(
            items=tuple(tables),
            views=tuple(views),
            cursor=next_cursor,
            is_last_page=not has_more,
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
                        SELECT a.attnum, a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod),
                               a.attnotnull, pg_get_expr(d.adbin, d.adrelid) AS default_expr,
                               a.attidentity, a.attgenerated
                        FROM pg_attribute a
                        JOIN pg_class c ON c.oid = a.attrelid
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                        WHERE n.nspname = %s AND c.relname = %s AND a.attnum > 0 AND NOT a.attisdropped
                        ORDER BY a.attnum
                    """, (schema_name, object_name))
                    for r in cur.fetchall():
                        num, name, ntype, notnull, dflt, ident, gen = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
                        is_lob = any(t in ntype.lower() for t in ("bytea", "text", "json", "jsonb", "xml"))
                        cols.append(
                            ColumnPhysicalMetadata(
                                name=name,
                                ordinal_position=num,
                                native_type=ntype.upper(),
                                nullable=not bool(notnull),
                                default_expression=dflt,
                                is_identity=bool(ident and ident in ('a', 'd')),
                                identity_generation="ALWAYS" if ident == 'a' else ("BY DEFAULT" if ident == 'd' else None),
                                is_computed=bool(gen and gen == 's'),
                                is_lob=is_lob,
                            )
                        )

                    # 2. Constraints (PK, FK, Unique, Check)
                    cur.execute("""
                        SELECT conname, contype, pg_get_constraintdef(c.oid)
                        FROM pg_constraint c
                        JOIN pg_class cls ON cls.oid = c.conrelid
                        JOIN pg_namespace n ON n.oid = cls.relnamespace
                        WHERE n.nspname = %s AND cls.relname = %s
                    """, (schema_name, object_name))
                    for r in cur.fetchall():
                        cname, ctype, cdef = r[0], r[1], r[2]
                        if ctype == 'p':
                            # Primary key
                            pk_cols = [c.name for c in cols if c.name in cdef]
                            primary_key = PrimaryKeyFacts(name=cname, table_name=object_name, columns=tuple(pk_cols), schema_name=schema_name)
                        elif ctype == 'u':
                            u_cols = [c.name for c in cols if c.name in cdef]
                            uniques.append(UniqueConstraintFacts(name=cname, table_name=object_name, columns=tuple(u_cols), schema_name=schema_name))
                        elif ctype == 'c':
                            checks.append(CheckConstraintFacts(name=cname, table_name=object_name, check_clause=cdef, schema_name=schema_name))

                    # 3. Foreign Keys
                    cur.execute("""
                        SELECT c.conname,
                               ARRAY(SELECT attname FROM pg_attribute WHERE attrelid = c.conrelid AND attnum = ANY(c.conkey)) as src_cols,
                               ref_ns.nspname as ref_schema,
                               ref_cls.relname as ref_table,
                               ARRAY(SELECT attname FROM pg_attribute WHERE attrelid = c.confrelid AND attnum = ANY(c.confkey)) as ref_cols,
                               c.confupdtype, c.confdeltype
                        FROM pg_constraint c
                        JOIN pg_class cls ON cls.oid = c.conrelid
                        JOIN pg_namespace n ON n.oid = cls.relnamespace
                        JOIN pg_class ref_cls ON ref_cls.oid = c.confrelid
                        JOIN pg_namespace ref_ns ON ref_ns.oid = ref_cls.relnamespace
                        WHERE n.nspname = %s AND cls.relname = %s AND c.contype = 'f'
                    """, (schema_name, object_name))
                    for r in cur.fetchall():
                        fks.append(
                            ForeignKeyFacts(
                                name=r[0],
                                table_name=object_name,
                                columns=tuple(r[1]),
                                referenced_schema=r[2],
                                referenced_table=r[3],
                                referenced_columns=tuple(r[4]),
                                schema_name=schema_name,
                            )
                        )

                    # 4. Indexes
                    cur.execute("""
                        SELECT i.relname, am.amname, ix.indisunique, ix.indisprimary, pg_get_indexdef(ix.indexrelid)
                        FROM pg_index ix
                        JOIN pg_class i ON i.oid = ix.indexrelid
                        JOIN pg_class t ON t.oid = ix.indrelid
                        JOIN pg_namespace n ON n.oid = t.relnamespace
                        JOIN pg_am am ON am.oid = i.relam
                        WHERE n.nspname = %s AND t.relname = %s
                    """, (schema_name, object_name))
                    for r in cur.fetchall():
                        iname, iam, is_u, is_pk, idef = r[0], r[1], r[2], r[3], r[4]
                        am_enum = IndexAccessMethod.BTREE
                        if iam.lower() == "gin":
                            am_enum = IndexAccessMethod.GIN
                        elif iam.lower() == "gist":
                            am_enum = IndexAccessMethod.GIST
                        elif iam.lower() == "brin":
                            am_enum = IndexAccessMethod.BRIN
                        elif iam.lower() == "hash":
                            am_enum = IndexAccessMethod.HASH

                        idx_cols = tuple(c.name for c in cols if c.name in idef)
                        indexes.append(
                            IndexFacts(
                                name=iname,
                                table_name=object_name,
                                schema_name=schema_name,
                                columns=idx_cols,
                                is_unique=is_u,
                                is_primary=is_pk,
                                access_method=am_enum,
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying pg structure for {schema_name}.{object_name}: {exc}")
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

        results: dict[str, ObjectStructureFacts] = {}
        names_list = list(object_names)
        try:
            with connection.cursor() as cur:
                # 1. Bulk Columns
                cur.execute("""
                    SELECT c.relname, a.attnum, a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod),
                           a.attnotnull, pg_get_expr(d.adbin, d.adrelid) AS default_expr,
                           a.attidentity, a.attgenerated
                    FROM pg_attribute a
                    JOIN pg_class c ON c.oid = a.attrelid
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                    WHERE n.nspname = %s AND c.relname = ANY(%s) AND a.attnum > 0 AND NOT a.attisdropped
                    ORDER BY c.relname, a.attnum
                """, (schema_name, names_list))
                
                cols_by_tbl: dict[str, list[ColumnPhysicalMetadata]] = {name: [] for name in object_names}
                for r in cur.fetchall():
                    tname, num, name, ntype, notnull, dflt, ident, gen = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]
                    is_lob = any(t in ntype.lower() for t in ("bytea", "text", "json", "jsonb", "xml"))
                    cols_by_tbl.setdefault(tname, []).append(
                        ColumnPhysicalMetadata(
                            name=name,
                            ordinal_position=num,
                            native_type=ntype.upper(),
                            nullable=not bool(notnull),
                            default_expression=dflt,
                            is_identity=bool(ident and ident in ('a', 'd')),
                            identity_generation="ALWAYS" if ident == 'a' else ("BY DEFAULT" if ident == 'd' else None),
                            is_computed=bool(gen and gen == 's'),
                            is_lob=is_lob,
                        )
                    )

                # 2. Bulk Constraints
                cur.execute("""
                    SELECT c.relname, con.conname, con.contype, pg_get_constraintdef(con.oid) AS def_str,
                           ARRAY(SELECT attname FROM pg_attribute WHERE attrelid = con.conrelid AND attnum = ANY(con.conkey)) AS con_cols,
                           fn.nspname AS ref_sch, fc.relname AS ref_tbl,
                           ARRAY(SELECT attname FROM pg_attribute WHERE attrelid = con.confrelid AND attnum = ANY(con.confkey)) AS ref_cols,
                           con.confupdtype, con.confdeltype, con.condeferrable, con.condeferred
                    FROM pg_constraint con
                    JOIN pg_class c ON c.oid = con.conrelid
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    LEFT JOIN pg_class fc ON fc.oid = con.confrelid
                    LEFT JOIN pg_namespace fn ON fn.oid = fc.relnamespace
                    WHERE n.nspname = %s AND c.relname = ANY(%s)
                """, (schema_name, names_list))
                
                pk_by_tbl: dict[str, Optional[PrimaryKeyFacts]] = {}
                fks_by_tbl: dict[str, list[ForeignKeyFacts]] = {name: [] for name in object_names}
                uniques_by_tbl: dict[str, list[UniqueConstraintFacts]] = {name: [] for name in object_names}
                checks_by_tbl: dict[str, list[CheckConstraintFacts]] = {name: [] for name in object_names}

                for r in cur.fetchall():
                    tname, conname, contype, def_str, cnames, f_sch, f_tbl, f_cnames, upda, dela, defer, def_init = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11]
                    cols_tup = tuple(cnames) if cnames else ()
                    if contype == 'p':
                        pk_by_tbl[tname] = PrimaryKeyFacts(name=conname, table_name=tname, columns=cols_tup, schema_name=schema_name)
                    elif contype == 'u':
                        uniques_by_tbl.setdefault(tname, []).append(UniqueConstraintFacts(name=conname, table_name=tname, columns=cols_tup, schema_name=schema_name))
                    elif contype == 'c':
                        checks_by_tbl.setdefault(tname, []).append(CheckConstraintFacts(name=conname, table_name=tname, check_clause=def_str or "", schema_name=schema_name))
                    elif contype == 'f':
                        upd_map = {'a': 'NO ACTION', 'r': 'RESTRICT', 'c': 'CASCADE', 'n': 'SET NULL', 'd': 'SET DEFAULT'}
                        fks_by_tbl.setdefault(tname, []).append(
                            ForeignKeyFacts(
                                name=conname,
                                table_name=tname,
                                columns=cols_tup,
                                referenced_schema=f_sch or schema_name,
                                referenced_table=f_tbl or "",
                                referenced_columns=tuple(f_cnames) if f_cnames else (),
                                schema_name=schema_name,
                                on_update=upd_map.get(upda, "NO ACTION"),
                                on_delete=upd_map.get(dela, "NO ACTION"),
                                is_deferrable=bool(defer),
                            )
                        )

                # 3. Bulk Indexes
                cur.execute("""
                    SELECT c.relname, ic.relname AS idx_name, am.amname AS access_method,
                           i.indisunique, i.indisprimary, pg_get_indexdef(i.indexrelid) AS index_def,
                           ARRAY(
                               SELECT a.attname 
                               FROM unnest(i.indkey) k 
                               JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k
                           ) AS col_names
                    FROM pg_index i
                    JOIN pg_class c ON c.oid = i.indrelid
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    JOIN pg_class ic ON ic.oid = i.indexrelid
                    JOIN pg_am am ON am.oid = ic.relam
                    WHERE n.nspname = %s AND c.relname = ANY(%s)
                """, (schema_name, names_list))
                indexes_by_tbl: dict[str, list[IndexFacts]] = {name: [] for name in object_names}
                for r in cur.fetchall():
                    tname, iname, amname, is_u, is_p, idef, cnames = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
                    am_enum = IndexAccessMethod.BTREE
                    if amname == 'hash':
                        am_enum = IndexAccessMethod.HASH
                    elif amname == 'gin':
                        am_enum = IndexAccessMethod.GIN
                    elif amname == 'gist':
                        am_enum = IndexAccessMethod.GIST
                    elif amname == 'brin':
                        am_enum = IndexAccessMethod.BRIN

                    indexes_by_tbl.setdefault(tname, []).append(
                        IndexFacts(
                            name=iname,
                            table_name=tname,
                            columns=tuple(cnames) if cnames else (),
                            schema_name=schema_name,
                            is_unique=bool(is_u),
                            is_primary=bool(is_p),
                            access_method=am_enum,
                            expression=idef,
                        )
                    )

                for name in object_names:
                    results[name] = ObjectStructureFacts(
                        table_name=name,
                        schema_name=schema_name,
                        columns=tuple(cols_by_tbl.get(name, [])),
                        primary_key=pk_by_tbl.get(name),
                        foreign_keys=tuple(fks_by_tbl.get(name, [])),
                        unique_constraints=tuple(uniques_by_tbl.get(name, [])),
                        check_constraints=tuple(checks_by_tbl.get(name, [])),
                        indexes=tuple(indexes_by_tbl.get(name, [])),
                    )
        except Exception as exc:
            logger.warning(f"Bulk structure discovery failed for schema '{schema_name}': {exc}")
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
        try:
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT c.relname,
                           COALESCE(c.reltuples, 0)::bigint AS est_rows,
                           pg_relation_size(c.oid) AS data_bytes,
                           pg_indexes_size(c.oid) AS idx_bytes,
                           COALESCE(pg_total_relation_size(c.reltoastrelid), 0) AS toast_bytes
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = %s AND c.relname = ANY(%s)
                """, (schema_name, names_list))
                for r in cur.fetchall():
                    rname, rcount, dbytes, ibytes, tbytes = r[0], r[1], r[2], r[3], r[4]
                    results[rname] = TableSizeFacts(
                        table_name=rname,
                        schema_name=schema_name,
                        row_count=max(0, int(rcount)),
                        count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
                        data_bytes=max(0, int(dbytes)),
                        index_bytes=max(0, int(ibytes)),
                        lob_or_toast_bytes=max(0, int(tbytes)),
                    )
        except Exception as exc:
            logger.warning(f"Bulk stats discovery failed for schema '{schema_name}': {exc}")
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
        udts = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    # Routines (Functions & Procedures)
                    cur.execute("""
                        SELECT r.routine_name, r.routine_type, r.data_type, r.routine_definition,
                               r.security_type, r.is_deterministic
                        FROM information_schema.routines r
                        WHERE r.routine_schema = %s
                        ORDER BY r.routine_name
                    """, (schema_name,))
                    for r in cur.fetchall():
                        rname, rtype, dtype, rdef, sec, is_det = r[0], r[1], r[2], r[3], r[4], r[5]
                        routines.append(
                            RoutineFacts(
                                name=rname,
                                schema_name=schema_name,
                                routine_type=RoutineType.PROCEDURE if rtype == 'PROCEDURE' else RoutineType.FUNCTION,
                                return_type=dtype,
                                definition=rdef,
                                is_deterministic=(is_det == 'YES'),
                                is_security_definer=(sec == 'DEFINER'),
                            )
                        )

                    # Triggers
                    cur.execute("""
                        SELECT trigger_name, event_object_table, action_timing, event_manipulation,
                               action_statement, action_orientation
                        FROM information_schema.triggers
                        WHERE trigger_schema = %s
                        ORDER BY trigger_name
                    """, (schema_name,))
                    for r in cur.fetchall():
                        trigname, tblname, timing, evt, stmt, orient = r[0], r[1], r[2], r[3], r[4], r[5]
                        triggers.append(
                            TriggerFacts(
                                name=trigname,
                                table_name=tblname,
                                schema_name=schema_name,
                                timing=timing,
                                event=evt,
                                definition=stmt,
                                is_row_level=(orient == 'ROW'),
                            )
                        )

                    # Sequences
                    cur.execute("""
                        SELECT sequence_name, start_value, increment, minimum_value, maximum_value, cycle_option
                        FROM information_schema.sequences
                        WHERE sequence_schema = %s
                        ORDER BY sequence_name
                    """, (schema_name,))
                    for r in cur.fetchall():
                        sequences.append(
                            SequenceFacts(
                                name=r[0],
                                schema_name=schema_name,
                                start_value=int(r[1]),
                                increment_by=int(r[2]),
                                min_value=int(r[3]),
                                max_value=int(r[4]),
                                is_cycling=(r[5] == "YES"),
                            )
                        )
            except Exception as exc:
                logger.warning(f"Error querying pg programmables in {schema_name}: {exc}")

        return ProgrammableInventory(
            routines=tuple(routines),
            triggers=tuple(triggers),
            sequences=tuple(sequences),
            udts=tuple(udts),
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
        key_cols = []
        bounds = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT partstrat, partnatts
                        FROM pg_partitioned_table pt
                        JOIN pg_class c ON c.oid = pt.partrelid
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = %s AND c.relname = %s
                    """, (schema_name, table_name))
                    row = cur.fetchone()
                    if row:
                        strat_char = row[0]
                        if strat_char == 'r':
                            strategy = PartitionStrategy.RANGE
                        elif strat_char == 'l':
                            strategy = PartitionStrategy.LIST
                        elif strat_char == 'h':
                            strategy = PartitionStrategy.HASH

                        # Partition bounds
                        cur.execute("""
                            SELECT child.relname, pg_get_expr(child.relpartbound, child.oid)
                            FROM pg_inherits i
                            JOIN pg_class parent ON parent.oid = i.inhparent
                            JOIN pg_class child ON child.oid = i.inhrelid
                            JOIN pg_namespace n ON n.oid = parent.relnamespace
                            WHERE n.nspname = %s AND parent.relname = %s
                        """, (schema_name, table_name))
                        for idx, r in enumerate(cur.fetchall()):
                            bounds.append(
                                PartitionBoundFacts(
                                    partition_name=r[0],
                                    strategy=strategy,
                                    lower_bound=r[1],
                                    partition_ordinal=idx + 1,
                                )
                            )
            except Exception as exc:
                logger.warning(f"Error discovering pg partitions for {schema_name}.{table_name}: {exc}")
                raise

        return PartitionFacts(
            table_name=table_name,
            schema_name=schema_name,
            strategy=strategy,
            key_columns=tuple(key_cols),
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
        row_count = 0
        data_bytes = 0
        idx_bytes = 0
        toast_bytes = 0

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT COALESCE(c.reltuples, 0)::bigint,
                               pg_relation_size(c.oid) AS data_bytes,
                               pg_indexes_size(c.oid) AS idx_bytes,
                               COALESCE(pg_total_relation_size(c.reltoastrelid), 0) AS toast_bytes
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = %s AND c.relname = %s
                    """, (schema_name, table_name))
                    row = cur.fetchone()
                    if row:
                        row_count = max(0, int(row[0]))
                        data_bytes = max(0, int(row[1]))
                        idx_bytes = max(0, int(row[2]))
                        toast_bytes = max(0, int(row[3]))
            except Exception as exc:
                logger.warning(f"Error querying stats for {schema_name}.{table_name}: {exc}")

        return TableSizeFacts(
            table_name=table_name,
            schema_name=schema_name,
            row_count=row_count,
            count_accuracy=CountAccuracy.CATALOG_ESTIMATE,
            data_bytes=data_bytes,
            index_bytes=idx_bytes,
            lob_or_toast_bytes=toast_bytes,
        )

    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SHOW transaction_read_only")
                    row = cur.fetchone()
                    if row and str(row[0]).lower() in ("on", "true", "1"):
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
                    cur.execute("SELECT has_schema_privilege('pg_catalog', 'USAGE')")
                    row = cur.fetchone()
                    cat_read = ThreeStatePermission.PROVEN if (row and row[0]) else ThreeStatePermission.DENIED
            except Exception:
                cat_read = ThreeStatePermission.UNKNOWN

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
        server_enc = "UTF-8"
        collate = "C"
        tz = "UTC"
        max_conn = 100
        exts = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SHOW server_encoding")
                    r = cur.fetchone()
                    if r:
                        server_enc = str(r[0])

                    cur.execute("SHOW lc_collate")
                    r = cur.fetchone()
                    if r:
                        collate = str(r[0])

                    cur.execute("SHOW TimeZone")
                    r = cur.fetchone()
                    if r:
                        tz = str(r[0])

                    cur.execute("SHOW max_connections")
                    r = cur.fetchone()
                    if r:
                        max_conn = int(r[0])

                    cur.execute("SELECT extname FROM pg_extension ORDER BY extname")
                    exts = [str(r[0]) for r in cur.fetchall()]
            except Exception as exc:
                logger.warning(f"Error fetching pg environment: {exc}")

        return ConfigurationFacts(
            charset=CharsetFacts(server_encoding=server_enc),
            collation=CollationFacts(default_collation=collate),
            timezone=TimezoneFacts(database_timezone=tz),
            limits=LimitsFacts(max_connections=max_conn),
            installed_extensions=tuple(exts),
        )

    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        is_replica = False
        nodes = []

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT pg_is_in_recovery()")
                    row = cur.fetchone()
                    if row:
                        is_replica = bool(row[0])

                    # Inspect streaming replicas if on primary
                    if not is_replica:
                        cur.execute("""
                            SELECT client_addr, client_port, state,
                                   EXTRACT(EPOCH FROM (now() - replay_lag)) * 1000 AS lag_ms
                            FROM pg_stat_replication
                        """)
                        for r in cur.fetchall():
                            nodes.append(
                                ClusterNodeFacts(
                                    node_id=f"replica_{r[0]}:{r[1]}",
                                    host=str(r[0]) if r[0] else "unknown",
                                    port=int(r[1]) if r[1] else 5432,
                                    role=NodeRole.REPLICA,
                                    replication_lag_ms=int(r[3]) if r[3] is not None else 0,
                                )
                            )
            except Exception as exc:
                logger.warning(f"Error discovering pg topology: {exc}")

        connected_role = NodeRole.REPLICA if is_replica else NodeRole.PRIMARY
        nodes.insert(0, ClusterNodeFacts(node_id="connected_node", host=spec.host or "localhost", port=spec.port or 5432, role=connected_role))

        return TopologySnapshot(
            is_clustered=len(nodes) > 1,
            connected_node_role=connected_role,
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
                blocker_reasons=("PostgreSQL connection not established",),
            )
        wal_level = "replica"
        max_slots = 10
        used_slots = 0
        starting_lsn = None

        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SHOW wal_level")
                    r = cur.fetchone()
                    if r:
                        wal_level = str(r[0]).lower()

                    cur.execute("SHOW max_replication_slots")
                    r = cur.fetchone()
                    if r:
                        max_slots = int(r[0])

                    cur.execute("SELECT count(*) FROM pg_replication_slots")
                    r = cur.fetchone()
                    if r:
                        used_slots = int(r[0])

                    cur.execute("SELECT pg_current_wal_lsn()")
                    r = cur.fetchone()
                    if r:
                        starting_lsn = str(r[0])
            except Exception as exc:
                logger.warning(f"Error discovering pg CDC prerequisites: {exc}")

        is_wal_logical = (wal_level == "logical")
        avail_slots = max(0, max_slots - used_slots)
        is_ready = is_wal_logical and (avail_slots > 0)
        blockers = []
        if not is_wal_logical:
            blockers.append(f"wal_level is '{wal_level}' (must be 'logical' for CDC).")
        if avail_slots <= 0:
            blockers.append(f"No available replication slots ({used_slots}/{max_slots} used).")

        return CDCPrerequisiteSnapshot(
            is_cdc_ready=is_ready,
            mechanism=CDCMechanism.POSTGRES_LOGICAL_DECODING,
            starting_position=StartingCommitPosition(lsn=starting_lsn) if starting_lsn else None,
            is_wal_level_logical=is_wal_logical,
            max_replication_slots=max_slots,
            available_replication_slots=avail_slots,
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
                cur.execute(f"SET statement_timeout = {int(timeout_seconds * 1000)}")
                cur.execute(f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {limit}')
                cols = [d[0] for d in cur.description] if cur.description else []
                for r in cur.fetchall():
                    rows.append(dict(zip(cols, r)))
            return DeterministicSampler.package_sample(table_name, schema_name, cols, rows)
        except Exception as exc:
            logger.warning(f"Error sampling pg table {schema_name}.{table_name}: {exc}")
            return DeterministicSampler.package_failure(table_name, schema_name, str(exc))

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        if connection is not None and hasattr(connection, "cursor"):
            try:
                with connection.cursor() as cur:
                    cur.execute("SELECT txid_current()")
                    r = cur.fetchone()
                    if r:
                        return str(r[0])
            except Exception:
                pass
        return None


PostgreSQLDiscoveryStrategy = PostgresDiscoveryStrategy
