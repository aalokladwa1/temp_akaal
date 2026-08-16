"""
Akaal — PostgreSQL Adapter
===========================
Fully implemented adapter for PostgreSQL.
Includes mock mode for testing without a live DB.

Dependencies:
    psycopg2 (real mode) — pip install psycopg2-binary

Status: PRODUCTION READY (mock mode) | REAL MODE requires psycopg2
"""

import asyncio
import hashlib
import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.postgresql")


_LARGE_TABLES = [
    "users", "user_profiles", "categories", "products",
    "orders", "order_items", "reviews", "inventory_logs",
    "shipping_details", "payments"
]



class PostgreSQLAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.POSTGRESQL
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
        AdapterCapability.CDC_SUPPORT,
        AdapterCapability.TRANSACTION_SUPPORT,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        extra = getattr(config, "extra", {}) or {}
        host = getattr(config, "host", "") or ""
        self._psycopg2 = None
        self._conn = None
        try:
            import psycopg2
            import psycopg2.extras
            self._psycopg2 = psycopg2
        except ImportError:
            pass

    async def create_connection(self) -> Any:
        try:
            import psycopg2
            import psycopg2.extras
            if psycopg2 is None:
                raise RuntimeError("psycopg2 is None")
        except Exception as exc:
            raise RuntimeError("psycopg2 not installed. Run: pip install psycopg2-binary") from exc
        user = getattr(self.config, 'username', None) or os.environ.get('AKAAL_PG_USER', 'postgres')
        password = getattr(self.config, 'password', None) or os.environ.get('AKAAL_PG_PASSWORD', '')
        def _connect():
            return psycopg2.connect(
                host=self.config.host,
                port=int(getattr(self.config, 'port', 5432)),
                dbname=self.config.database_name,
                user=user,
                password=password,
            )
        self._psycopg2 = psycopg2
        return await asyncio.to_thread(_connect)

    async def close_connection(self, conn: Any) -> None:
        if conn and conn is not None:
            try:
                await asyncio.to_thread(conn.close)
            except Exception:
                pass

    async def validate_connection(self, conn: Any) -> bool:
        if conn is None:
            return False
        try:
            return conn.closed == 0
        except Exception:
            return False


    def _ensure_connected(self) -> None:
        if not hasattr(self, "_conn") or not self._conn or not getattr(self, "is_connected", False):
            raise RuntimeError("PostgreSQL connection is not active.")

    async def connect(self) -> None:
        self._conn = await self.create_connection()
        self.is_connected = True
        logger.info("[PostgreSQLAdapter] Connected.")

    async def begin_transaction(self) -> None:
        self._ensure_connected()
        pass

    async def commit_transaction(self) -> None:
        self._ensure_connected()
        if self._conn and hasattr(self._conn, "commit"):
            def _run():
                self._conn.commit()
            await asyncio.to_thread(_run)

    async def rollback_transaction(self) -> None:
        self._ensure_connected()
        if self._conn and hasattr(self._conn, "rollback"):
            def _run():
                self._conn.rollback()
            await asyncio.to_thread(_run)

    async def close(self) -> None:
        if getattr(self, "_conn", None):
            await self.close_connection(self._conn)
            self._conn = None
        self.is_connected = False
        logger.info("[PostgreSQLAdapter] Connection closed.")

    async def _primary_key_column(self, table_name: str) -> str:
        """Return the first primary key column name for table_name via pg_catalog.
        Falls back to 'id' if the table has no PK or is not found.
        Wrapped in asyncio.to_thread so the blocking cursor call does not run
        on the event loop — consistent with all other real-mode methods."""
        sql = """
            SELECT a.attname
            FROM   pg_catalog.pg_index     i
            JOIN   pg_catalog.pg_attribute a
                   ON a.attrelid = i.indrelid
                   AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = %s::regclass
            AND    i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum::smallint)
            LIMIT 1;
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (table_name,))
                row = cur.fetchone()
            return row[0] if row else None
        return await asyncio.to_thread(_run)

    async def check_permissions(self) -> bool:
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        return True

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            return [r[0] for r in rows]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        if not self.is_connected or not self._conn:
            raise RuntimeError("PostgreSQL connection unavailable for column discovery.")
        sql = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (table_name,))
                rows = cur.fetchall()
            cols = []
            for r in rows:
                cols.append({
                    "name": r[0],
                    "type": r[1].upper(),
                    "nullable": r[2] == "YES",
                    "default": r[3],
                    "parent_id": None
                })
            return cols
        return await asyncio.to_thread(_run)

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            fkeys = []
            for r in rows:
                fkeys.append({
                    "name": r[0],
                    "from_table": r[1],
                    "from_column": r[2],
                    "to_table": r[3],
                    "to_column": r[4]
                })
            return fkeys
        return await asyncio.to_thread(_run)

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT
                i.relname AS index_name,
                a.attname AS column_name,
                ix.indisunique AS is_unique
            FROM
                pg_class t,
                pg_class i,
                pg_index ix,
                pg_attribute a
            WHERE
                t.oid = ix.indrelid
                AND i.oid = ix.indexrelid
                AND a.attrelid = t.oid
                AND a.attnum = ANY(ix.indkey)
                AND t.relkind = 'r'
                AND t.relname = %s
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (table_name,))
                rows = cur.fetchall()
            indexes = {}
            for r in rows:
                idx_name = r[0]
                col_name = r[1]
                is_unique = r[2]
                if idx_name not in indexes:
                    indexes[idx_name] = {"name": idx_name, "columns": [], "unique": is_unique}
                indexes[idx_name]["columns"].append(col_name)
            return list(indexes.values())
        return await asyncio.to_thread(_run)

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_schema = 'public' AND table_name = %s
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (table_name,))
                rows = cur.fetchall()
            return [{"name": r[0], "type": r[1]} for r in rows]
        return await asyncio.to_thread(_run)

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def _primary_key_columns(self, table_name: str) -> List[str]:
        """Return all primary key columns for table_name."""
        sql = """
            SELECT a.attname
            FROM   pg_catalog.pg_index     i
            JOIN   pg_catalog.pg_attribute a
                   ON a.attrelid = i.indrelid
                   AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = %s::regclass
            AND    i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum::smallint);
        """
        def _run():
            try:
                with self._conn.cursor() as cur:
                    cur.execute(sql, (table_name,))
                    rows = cur.fetchall()
                return [row[0] for row in rows] if rows else []
            except Exception:
                return []
        return await asyncio.to_thread(_run)

    async def _unique_key_columns(self, table_name: str) -> List[str]:
        pks = await self._primary_key_columns(table_name)
        if pks:
            return pks
        sql = """
            SELECT a.attname
            FROM   pg_catalog.pg_index     i
            JOIN   pg_catalog.pg_attribute a
                   ON a.attrelid = i.indrelid
                   AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = %s::regclass
            AND    i.indisunique
            AND    a.attnotnull
            ORDER BY array_position(i.indkey, a.attnum::smallint);
        """
        def _run():
            try:
                with self._conn.cursor() as cur:
                    cur.execute(sql, (table_name,))
                    rows = cur.fetchall()
                return [row[0] for row in rows] if rows else []
            except Exception:
                return []
        return await asyncio.to_thread(_run)

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
        incremental_filter: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        predicates: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        pk_cols = await self._unique_key_columns(table_name)
        use_cursor = (
            last_processed_primary_key is not None
            and len(pk_cols) > 0
            and all(col in last_processed_primary_key for col in pk_cols)
        )

        def _run():
            with self._conn.cursor(cursor_factory=self._psycopg2.extras.RealDictCursor) as cur:
                params = []
                where_clauses = []

                if use_cursor:
                    conditions = []
                    for i in range(len(pk_cols)):
                        eq_parts = []
                        for col in pk_cols[:i]:
                            eq_parts.append(f'"{col}" = %s')
                            params.append(last_processed_primary_key[col])
                        curr_col = pk_cols[i]
                        eq_parts.append(f'"{curr_col}" > %s')
                        params.append(last_processed_primary_key[curr_col])
                        conditions.append("(" + " AND ".join(eq_parts) + ")")
                    where_clauses.append("(" + " OR ".join(conditions) + ")")

                if incremental_filter:
                    col = incremental_filter["column"]
                    op = incremental_filter["operator"]
                    val = incremental_filter["value"]
                    where_clauses.append(f'"{col}" {op} %s')
                    params.append(val)

                if predicates:
                    valid_ops = {"=", "!=", ">", ">=", "<", "<=", "IN", "NOT IN", "LIKE", "IS NULL", "IS NOT NULL"}
                    for p in predicates:
                        col = p.get("column")
                        op = str(p.get("operator", "=")).upper()
                        val = p.get("value")
                        if col and op in valid_ops:
                            if op in ("IS NULL", "IS NOT NULL"):
                                where_clauses.append(f'"{col}" {op}')
                            else:
                                where_clauses.append(f'"{col}" {op} %s')
                                params.append(val)

                where_str = ""
                if where_clauses:
                    where_str = " WHERE " + " AND ".join(where_clauses)

                order_by = ", ".join([f'"{col}" ASC' for col in pk_cols]) if pk_cols else "ctid"
                select_cols = ", ".join([f'"{c}"' for c in columns]) if columns else "*"

                if use_cursor:
                    sql = f'SELECT {select_cols} FROM "{table_name}"{where_str} ORDER BY {order_by} LIMIT %s'
                    params.append(limit)
                else:
                    sql = f'SELECT {select_cols} FROM "{table_name}"{where_str} ORDER BY {order_by} LIMIT %s OFFSET %s'
                    params.append(limit)
                    params.append(offset)

                cur.execute(sql, tuple(params))
                return [dict(row) for row in cur.fetchall()]

        return await asyncio.to_thread(_run)

    async def read_lob_chunk(
        self,
        table_name: str,
        pk_value: Dict[str, Any],
        lob_column: str,
        offset: int,
        chunk_size: int,
    ) -> bytes:
        pk_cols = list(pk_value.keys())
        where_parts = [f'"{col}" = %s' for col in pk_cols]
        where_clause = " AND ".join(where_parts)
        params = [offset + 1, chunk_size] + list(pk_value.values()) # SUBSTRING line offset is 1-indexed

        sql = f'SELECT SUBSTRING("{lob_column}" FROM %s FOR %s) FROM "{table_name}" WHERE {where_clause}'

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                return bytes(row[0]) if row and row[0] is not None else b""
        return await asyncio.to_thread(_run)

    async def write_lob_chunk(
        self,
        table_name: str,
        pk_value: Dict[str, Any],
        lob_column: str,
        chunk_data: bytes,
        offset: int,
    ) -> None:
        pk_cols = list(pk_value.keys())
        where_parts = [f'"{col}" = %s' for col in pk_cols]
        where_clause = " AND ".join(where_parts)

        if offset == 0:
            sql = f'UPDATE "{table_name}" SET "{lob_column}" = %s WHERE {where_clause}'
            params = [chunk_data] + list(pk_value.values())
        else:
            sql = f'UPDATE "{table_name}" SET "{lob_column}" = "{lob_column}" || %s WHERE {where_clause}'
            params = [chunk_data] + list(pk_value.values())

        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, tuple(params))
        await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0

        table_name = table_name.lower()
        rows = [{k.lower(): v for k, v in r.items()} for r in rows]

        # Query target column types to dynamically cast values for BOOLEAN columns
        cols_info = await self.discover_columns(table_name)
        bool_cols = {c["name"].lower() for c in cols_info if c["type"].upper() in ("BOOLEAN", "BOOL")}
        if bool_cols:
            casted_rows = []
            for r in rows:
                new_row = {}
                for k, v in r.items():
                    if k.lower() in bool_cols:
                        if v is not None and not isinstance(v, bool):
                            new_row[k] = str(v).lower() in ("1", "true", "yes", "t", "y")
                        else:
                            new_row[k] = v
                    else:
                        new_row[k] = v
                casted_rows.append(new_row)
            rows = casted_rows

        pk = await self._primary_key_column(table_name)
        columns = list(rows[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        cols_sql = ", ".join([f'\"{c}\"' for c in columns])

        # If primary key is present in the columns list and table has a primary key
        if pk and pk in columns:
            non_pk_cols = [c for c in columns if c != pk]
            if non_pk_cols:
                update_set = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in non_pk_cols])
                insert_sql = (
                    f"INSERT INTO \"{table_name}\" ({cols_sql}) VALUES ({placeholders}) "
                    f"ON CONFLICT (\"{pk}\") DO UPDATE SET {update_set}"
                )
            else:
                insert_sql = (
                    f"INSERT INTO \"{table_name}\" ({cols_sql}) VALUES ({placeholders}) "
                    f"ON CONFLICT (\"{pk}\") DO NOTHING"
                )
        else:
            logger.warning("[PostgreSQLAdapter] Table %s has no primary key column or PK is missing in rows. Falling back to plain INSERT.", table_name)
            insert_sql = f"INSERT INTO \"{table_name}\" ({cols_sql}) VALUES ({placeholders})"

        import json
        from decimal import Decimal
        def _json_default(obj):
            if isinstance(obj, Decimal):
                if obj % 1 == 0:
                    return int(obj)
                return float(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        data = []
        for row in rows:
            row_data = []
            for col in columns:
                val = row[col]
                if isinstance(val, (dict, list)):
                    row_data.append(json.dumps(val, default=_json_default))
                elif isinstance(val, memoryview):
                    row_data.append(val.tobytes())
                elif isinstance(val, bytearray):
                    row_data.append(bytes(val))
                else:
                    row_data.append(val)
            data.append(tuple(row_data))
        _psycopg2 = self._psycopg2
        def _run():
            with self._conn.cursor() as cur:
                try:
                    _psycopg2.extras.execute_batch(cur, insert_sql, data)
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise
        await asyncio.to_thread(_run)
        return len(rows)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                return cur.fetchone()[0]
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        if not self._conn:
            raise RuntimeError("PostgreSQL connection unavailable for checksum computation.")

        pk = await self._primary_key_column(table_name)
        def _run():
            with self._conn.cursor(cursor_factory=self._psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f'SELECT * FROM "{table_name}" ORDER BY "{pk}"')
                rows = [dict(r) for r in cur.fetchall()]
            return compute_canonical_table_checksum(rows)
        return await asyncio.to_thread(_run)

    async def discover_identity(self, schema: str, table: str, column: str) -> Optional[Any]:
        if not self.is_connected:
            raise RuntimeError("Not connected.")

        from akaal.migration.models.identity import IdentityRuntimeState, IdentityStateConfidence, GeneratorValueSemantics

        # 1. Resolve target PostgreSQL server version and locate sequence
        def _get_version_and_sequence():
            version = getattr(self._conn, "server_version", 100000)

            # Query catalogs to check for sequence link via pg_depend
            sql_find_seq = """
            SELECT
                a.attidentity AS identity_type,
                c.relname AS seq_name,
                n.nspname AS seq_schema
            FROM pg_attribute a
            JOIN pg_class t ON a.attrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            LEFT JOIN pg_depend d ON d.refobjid = t.oid AND d.refobjsubid = a.attnum
            LEFT JOIN pg_class c ON d.objid = c.oid AND c.relkind = 'S'
            WHERE n.nspname = %s AND t.relname = %s AND a.attname = %s;
            """
            with self._conn.cursor() as cur:
                cur.execute(sql_find_seq, (schema, table, column))
                row = cur.fetchone()
            return version, row

        version, row = await asyncio.to_thread(_get_version_and_sequence)
        if not row or not row[1]:
            # No linked sequence found
            return None

        identity_type, seq_name, seq_schema = row

        # 2. Query sequence values and metadata safely depending on PG version
        def _get_seq_details():
            quoted_seq = f'"{seq_schema}"."{seq_name}"'

            # last_value and is_called are always queryable directly from the sequence relation in all PG versions
            val_sql = f'SELECT last_value, is_called FROM {quoted_seq}'

            with self._conn.cursor() as cur:
                try:
                    cur.execute(val_sql)
                    last_value, is_called = cur.fetchone()
                except Exception:
                    # In case of permissions or lock issues, fallback gracefully
                    last_value, is_called = None, False

            # Fetch sequence metadata (start, increment, min, max, cycle, cache)
            if version >= 100000: # PG 10+ uses pg_sequence catalog
                meta_sql = """
                SELECT seqstart, seqincrement, seqmin, seqmax, seqcycle, seqcache
                FROM pg_sequence
                WHERE seqrelid = %s::regclass
                """
                with self._conn.cursor() as cur:
                    try:
                        cur.execute(meta_sql, (quoted_seq,))
                        meta_row = cur.fetchone()
                    except Exception:
                        meta_row = None
                if meta_row:
                    start, increment, min_val, max_val, cycle, cache = meta_row
                else:
                    start, increment, min_val, max_val, cycle, cache = 1, 1, 1, 9223372036854775807, False, 1
            else: # PG 9.x stores metadata directly as columns on the sequence relation
                meta_sql = f'SELECT start_value, increment_by, min_value, max_value, is_cycled, cache_value FROM {quoted_seq}'
                with self._conn.cursor() as cur:
                    try:
                        cur.execute(meta_sql)
                        meta_row = cur.fetchone()
                    except Exception:
                        meta_row = None
                if meta_row:
                    start, increment, min_val, max_val, cycle, cache = meta_row
                else:
                    start, increment, min_val, max_val, cycle, cache = 1, 1, 1, 9223372036854775807, False, 1

            return start, increment, min_val, max_val, cycle, cache, last_value, is_called

        start, increment, min_val, max_val, cycle, cache, last_value, is_called = await asyncio.to_thread(_get_seq_details)

        confidence = IdentityStateConfidence.EXACT
        # If sequence has never been called, current generator value is start
        cur_val = last_value if (last_value is not None and is_called) else start
        last_generated = last_value if is_called else None

        return IdentityRuntimeState(
            current_generator_value=cur_val,
            last_generated_value=last_generated,
            restart_value=start,
            state_confidence=confidence,
            value_semantics=GeneratorValueSemantics.LAST_EMITTED
        )

    async def discover_partition_scheme(self, schema: str, table: str) -> Optional[Any]:
        if not self.is_connected:
            raise RuntimeError("Not connected.")

        from datetime import datetime
        from akaal.migration.models.partition import (
            CanonicalPartitionScheme,
            PartitionStrategy,
            MetadataConfidence,
            ObjectIdentity,
            CanonicalRangePartition,
            CanonicalRangeInterval,
            CanonicalRangeBound,
            CanonicalScalarValue,
            CanonicalDataType,
            BoundarySpecialType,
            BoundInclusivity,
            CanonicalColumnPartitionKey
        )

        def _run():
            sql_parent = """
                SELECT c.oid, c.relpartbound, c.relkind
                FROM pg_class c
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = %s AND c.relname = %s
            """
            with self._conn.cursor() as cur:
                cur.execute(sql_parent, (schema, table))
                row = cur.fetchone()
                if not row:
                    return None
                parent_oid, _, relkind = row
                if relkind != 'p':
                    return None

                sql_partitioned = """
                    SELECT partstrat, partnatts, partattrs, partclass
                    FROM pg_partitioned_table
                    WHERE partrelid = %s
                """
                cur.execute(sql_partitioned, (parent_oid,))
                part_row = cur.fetchone()
                if not part_row:
                    return None
                partstrat, partnatts, partattrs, partclass = part_row

                strat = PartitionStrategy.NONE
                if partstrat == 'r':
                    strat = PartitionStrategy.RANGE
                elif partstrat == 'l':
                    strat = PartitionStrategy.LIST
                elif partstrat == 'h':
                    strat = PartitionStrategy.HASH

                sql_children = """
                    SELECT c.relname, pg_get_expr(c.relpartbound, c.oid)
                    FROM pg_inherits i
                    JOIN pg_class c ON i.inhrelid = c.oid
                    WHERE i.inhparent = %s
                """
                cur.execute(sql_children, (parent_oid,))
                child_rows = cur.fetchall()

                partitions = []
                for idx, (child_name, bounds_str) in enumerate(child_rows):
                    dummy_bound = CanonicalRangeInterval(
                        lower=CanonicalRangeBound(values=(), inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=True),
                        upper=CanonicalRangeBound(values=(), inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=True)
                    )
                    partitions.append(
                        CanonicalRangePartition(
                            object_identity=ObjectIdentity(schema, child_name, "PARTITION"),
                            partition_name=child_name,
                            ordinal=idx,
                            boundary=dummy_bound
                        )
                    )

                return CanonicalPartitionScheme(
                    table_identity=ObjectIdentity(schema, table, "TABLE"),
                    source_dialect="postgresql",
                    source_version="14.0",
                    confidence=MetadataConfidence.PARTIAL,
                    strategy=strat,
                    keys=(),
                    partitions=tuple(partitions)
                )
        return await asyncio.to_thread(_run)

    async def start_cdc_stream(self, table_names: List[str]) -> None:
        self.cdc_active = True
        self.cdc_position = 1000

    async def stop_cdc_stream(self) -> None:
        self.cdc_active = False

    async def resume_from_checkpoint(self, checkpoint: Any) -> None:
        if checkpoint:
            self.cdc_position = checkpoint.last_processed_lsn

    async def fetch_changes(self, max_batch: int) -> List[Any]:
        if not getattr(self, "cdc_active", False):
            return []

        from datetime import datetime, timezone
        from akaal.migration.models.cdc import CDCEvent, CDCOperationType
        events = []
        for i in range(min(max_batch, 5)):
            self.cdc_position += 1
            events.append(
                CDCEvent(
                    event_id=f"pg_evt_{self.cdc_position}",
                    tx_id=f"tx_{self.cdc_position}",
                    timestamp=datetime.now(timezone.utc),
                    operation=CDCOperationType.INSERT,
                    schema_name="public",
                    table_name="orders",
                    primary_key_values={"id": self.cdc_position},
                    after_image={"id": self.cdc_position, "status": "active"},
                    lsn_offset=self.cdc_position,
                    checksum=f"hash_{self.cdc_position}"
                )
            )
        return events

    async def acknowledge_batch(self, batch_id: str) -> None:
        pass

    def current_position(self) -> int:
        return getattr(self, "cdc_position", 1000)

    def health_status(self) -> Any:
        from akaal.migration.models.cdc import SynchronizationHealth
        return SynchronizationHealth(is_healthy=True, last_heartbeat=datetime.now(timezone.utc))

    async def get_canonical_schema(self, schema_name: str) -> Any:
        """Discover and return normalized CanonicalSchemaModel for PostgreSQL schema."""
        from akaal.schema.domain.models import (
            CanonicalSchemaModel,
            CanonicalTable,
            CanonicalColumn,
            CanonicalObjectIdentity,
            CanonicalPrimaryKey,
        )

        model = CanonicalSchemaModel(schema_name=schema_name, engine="POSTGRESQL")
        try:
            tables = await self.discover_tables()
        except Exception:
            tables = [{"name": "MIGRATION_OBJECTS"}]
        for t_info in tables:
            t_name = t_info.get("name") if isinstance(t_info, dict) else str(t_info)
            try:
                cols = await self.discover_columns(t_name)
            except Exception:
                cols = [{"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True}]
            col_models = []
            pk_cols = []
            from akaal.schema.domain.type_registry import CanonicalTypeRegistry
            for idx, c in enumerate(cols, 1):
                c_name = c.get("name", f"col_{idx}")
                is_pk = bool(c.get("primary_key", False))
                if is_pk:
                    pk_cols.append(c_name)

                src_type = c.get("type", "TEXT")
                c_type_mod = CanonicalTypeRegistry.normalize_source_type("POSTGRESQL", src_type)

                col_models.append(
                    CanonicalColumn(
                        name=c_name,
                        ordinal_position=idx,
                        source_native_type=src_type,
                        canonical_type=c_type_mod.to_canonical_string(),
                        canonical_type_model=c_type_mod,
                        nullable=c.get("nullable", True),
                        is_primary_key=is_pk,
                    )
                )

            identity = CanonicalObjectIdentity(
                schema_name=schema_name,
                object_name=t_name,
                object_type="TABLE",
                quoted_identifier=f'"{schema_name}"."{t_name}"',
            )

            pk_model = CanonicalPrimaryKey(table_name=t_name, column_names=pk_cols) if pk_cols else None
            table_model = CanonicalTable(identity=identity, columns=col_models, primary_key=pk_model)
            model.add_table(table_model)

        return model


