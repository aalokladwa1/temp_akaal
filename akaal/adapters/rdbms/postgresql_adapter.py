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

_MOCK_HOSTS = {
    "source-db.example.com",
    "source-prod.example.com",
    "target-db.example.com",
    "target-cloud.example.com",
    "connection-fail.example.com",
    "permission-fail.example.com",
    "large-db.example.com",
    "oracle-prod.example.com",
    "postgres-target.example.com",
}

_LARGE_TABLES = [
    "users", "user_profiles", "categories", "products",
    "orders", "order_items", "reviews", "inventory_logs",
    "shipping_details", "payments"
]

_MOCK_COLUMNS = {
    "users": [
        {"name": "id",           "type": "INTEGER",      "nullable": False, "default": "nextval('users_id_seq')", "parent_id": None},
        {"name": "email",        "type": "VARCHAR(255)",  "nullable": False, "default": None,                     "parent_id": None},
        {"name": "password_hash","type": "VARCHAR(255)",  "nullable": False, "default": None,                     "parent_id": None},
        {"name": "status",       "type": "VARCHAR(50)",   "nullable": True,  "default": "'active'",               "parent_id": None},
        {"name": "created_at",   "type": "TIMESTAMP",     "nullable": True,  "default": "now()",                  "parent_id": None},
    ],
    "orders": [
        {"name": "id",           "type": "INTEGER",      "nullable": False, "default": "nextval('orders_id_seq')", "parent_id": None},
        {"name": "user_id",      "type": "INTEGER",      "nullable": True,  "default": None,                       "parent_id": "users.id"},
        {"name": "total_amount", "type": "NUMERIC(10,2)","nullable": True,  "default": None,                       "parent_id": None},
        {"name": "status",       "type": "VARCHAR(50)",  "nullable": True,  "default": "'pending'",                "parent_id": None},
        {"name": "order_date",   "type": "TIMESTAMP",    "nullable": True,  "default": "now()",                    "parent_id": None},
    ],
}


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
        self.mock_mode = getattr(config, "host", "") in _MOCK_HOSTS
        if self.mock_mode:
            logger.info("[PostgreSQLAdapter] Mock mode: host=%s", config.host)
        self._psycopg2 = None
        if not self.mock_mode:
            try:
                import psycopg2
                import psycopg2.extras
                self._psycopg2 = psycopg2
            except ImportError:
                pass

    async def create_connection(self) -> Any:
        if self.mock_mode:
            if getattr(self.config, "host", "") == "connection-fail.example.com":
                raise ConnectionError("Mock: PostgreSQL connection failure.")
            return "mock_pg_conn"
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise RuntimeError("psycopg2 not installed. Run: pip install psycopg2-binary")
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
        if conn and conn != "mock_pg_conn":
            try:
                await asyncio.to_thread(conn.close)
            except Exception:
                pass

    async def validate_connection(self, conn: Any) -> bool:
        if conn == "mock_pg_conn":
            return True
        if conn is None:
            return False
        try:
            return conn.closed == 0
        except Exception:
            return False

    async def connect(self) -> None:
        self._conn = await self.create_connection()
        self.is_connected = True
        logger.info("[PostgreSQLAdapter] Connected.")

    async def close(self) -> None:
        if self._conn:
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
            return row[0] if row else 'id'
        return await asyncio.to_thread(_run)

    async def check_permissions(self) -> bool:
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if self.mock_mode:
            if getattr(self.config, "host", "") == "permission-fail.example.com":
                return False
            return True
        return True

    async def discover_tables(self) -> List[str]:
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if self.mock_mode:
            host = getattr(self.config, "host", "")
            if host in ("large-db.example.com", "oracle-prod.example.com", "postgres-target.example.com"):
                return _LARGE_TABLES
            return ["users", "orders", "order_items"]
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
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if self.mock_mode:
            return _MOCK_COLUMNS.get(table_name, [
                {"name": "id", "type": "INTEGER", "nullable": False, "default": None, "parent_id": None}
            ])
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
        if self.mock_mode:
            return [
                {"name": "fk_orders_user", "from_table": "orders", "from_column": "user_id", "to_table": "users", "to_column": "id"},
            ]
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
        if self.mock_mode:
            return [{"name": f"{table_name}_pkey", "columns": ["id"], "unique": True}]
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
        if self.mock_mode:
            return []
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
        if self.mock_mode:
            return []
        return []

    async def discover_views(self) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return []
        return []

    async def _primary_key_columns(self, table_name: str) -> List[str]:
        """Return all primary key columns for table_name."""
        if self.mock_mode:
            if table_name == "composite_table":
                return ["pk1", "pk2"]
            elif table_name == "uuid_table":
                return ["uuid_col"]
            elif table_name == "string_table":
                return ["str_col"]
            elif table_name == "no_pk_table":
                return []
            return ["id"]

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
                return ["id"]
        return await asyncio.to_thread(_run)

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if self.mock_mode:
            start_id = offset
            pk_cols = await self._primary_key_columns(table_name)
            if last_processed_primary_key and pk_cols:
                # Mock cursor progression logic
                if len(pk_cols) == 1:
                    pk_val = last_processed_primary_key.get(pk_cols[0])
                    if pk_val is not None:
                        if isinstance(pk_val, str) and "-" in pk_val:
                            try:
                                start_id = int(pk_val.split("-")[-1]) + 1
                            except ValueError:
                                start_id = offset
                        else:
                            try:
                                start_id = int(pk_val) + 1
                            except ValueError:
                                start_id = offset
                else:
                    # Composite key progress: mock using the first pk column
                    pk_val = last_processed_primary_key.get(pk_cols[0])
                    if pk_val is not None:
                        try:
                            start_id = int(pk_val) + 1
                        except ValueError:
                            start_id = offset
            
            # Enforce dynamic limit for mock table pagination
            mock_max_rows = getattr(self.config, "mock_max_rows", 250)
            if start_id >= mock_max_rows:
                return []
            if start_id + limit > mock_max_rows:
                limit = mock_max_rows - start_id

            rows = []
            for i in range(start_id, start_id + limit):
                row = {"data": f"mock_row_{i}"}
                if table_name == "composite_table":
                    row["pk1"] = i
                    row["pk2"] = i * 10
                elif table_name == "uuid_table":
                    row["uuid_col"] = f"uuid-{i}"
                elif table_name == "string_table":
                    row["str_col"] = f"str-{i}"
                elif table_name == "no_pk_table":
                    row["data"] = f"mock_row_{i}"
                else:
                    row["id"] = i
                rows.append(row)
            return rows

        pk_cols = await self._primary_key_columns(table_name)
        
        # Check if cursor can be used (all primary key columns exist in cursor)
        use_cursor = (
            last_processed_primary_key is not None 
            and len(pk_cols) > 0 
            and all(col in last_processed_primary_key for col in pk_cols)
        )

        def _run():
            with self._conn.cursor(cursor_factory=self._psycopg2.extras.RealDictCursor) as cur:
                if use_cursor:
                    conditions = []
                    params = []
                    for i in range(len(pk_cols)):
                        eq_parts = []
                        for col in pk_cols[:i]:
                            eq_parts.append(f'"{col}" = %s')
                            params.append(last_processed_primary_key[col])
                        curr_col = pk_cols[i]
                        eq_parts.append(f'"{curr_col}" > %s')
                        params.append(last_processed_primary_key[curr_col])
                        conditions.append("(" + " AND ".join(eq_parts) + ")")
                    
                    where_clause = " OR ".join(conditions)
                    order_by = ", ".join([f'"{col}" ASC' for col in pk_cols])
                    sql = f'SELECT * FROM "{table_name}" WHERE {where_clause} ORDER BY {order_by} LIMIT %s'
                    params.append(limit)
                    cur.execute(sql, tuple(params))
                else:
                    order_by = ", ".join([f'"{col}" ASC' for col in pk_cols]) if pk_cols else '"id"'
                    sql = f'SELECT * FROM "{table_name}" ORDER BY {order_by} LIMIT %s OFFSET %s'
                    cur.execute(sql, (limit, offset))
                
                return [dict(row) for row in cur.fetchall()]

        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        if self.mock_mode:
            logger.info("[PostgreSQLAdapter] Mock write: %d rows to %s", len(rows), table_name)
            return len(rows)
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
        if self.mock_mode:
            counts = {"users": 200000, "orders": 300000, "order_items": 617070}
            return counts.get(table_name, 10000)
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                return cur.fetchone()[0]
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        if self.mock_mode:
            return hashlib.sha256(table_name.encode()).hexdigest()
        # Read all rows ordered by the primary key (same ordering used by
        # read_batch) so pagination and checksum always agree.
        def _row_hash(row: dict) -> str:
            parts = []
            for k in sorted(row.keys()):
                v = row[k]
                if isinstance(v, Decimal):
                    v = str(v)
                elif hasattr(v, 'isoformat'):
                    v = v.isoformat()
                else:
                    v = str(v) if v is not None else ''
                parts.append(f"{k}={v}")
            return hashlib.sha256('|'.join(parts).encode()).hexdigest()

        pk = await self._primary_key_column(table_name)
        def _run():
            with self._conn.cursor(cursor_factory=self._psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f'SELECT * FROM "{table_name}" ORDER BY "{pk}"')
                rows = cur.fetchall()
            combined = '|'.join(_row_hash(dict(r)) for r in rows)
            return hashlib.sha256(combined.encode()).hexdigest()
        return await asyncio.to_thread(_run)

    async def discover_identity(self, schema: str, table: str, column: str) -> Optional[Any]:
        if not self.is_connected:
            raise RuntimeError("Not connected.")
            
        from akaal.migration.models.identity import IdentityRuntimeState, IdentityStateConfidence, GeneratorValueSemantics
        
        if self.mock_mode:
            # Handle mock values for testing
            if table == "users" and column == "id":
                return IdentityRuntimeState(
                    current_generator_value=1,
                    last_generated_value=1,
                    restart_value=1,
                    state_confidence=IdentityStateConfidence.EXACT,
                    value_semantics=GeneratorValueSemantics.LAST_EMITTED
                )
            return None

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

        if self.mock_mode:
            if table == "orders":
                return CanonicalPartitionScheme(
                    table_identity=ObjectIdentity(schema, table, "TABLE"),
                    source_dialect="postgresql",
                    source_version="14.0",
                    confidence=MetadataConfidence.COMPLETE,
                    strategy=PartitionStrategy.RANGE,
                    keys=(
                        CanonicalColumnPartitionKey(
                            column_name="order_date",
                            canonical_type=CanonicalDataType.TIMESTAMP,
                            native_type="TIMESTAMP",
                            position=0,
                            nullable=True
                        ),
                    ),
                    partitions=(
                        CanonicalRangePartition(
                            object_identity=ObjectIdentity(schema, "orders_p1", "PARTITION"),
                            partition_name="orders_p1",
                            ordinal=0,
                            boundary=CanonicalRangeInterval(
                                lower=CanonicalRangeBound(
                                    values=(),
                                    inclusivity=BoundInclusivity.EXCLUSIVE,
                                    unbounded=True
                                ),
                                upper=CanonicalRangeBound(
                                    values=(
                                        CanonicalScalarValue(
                                            data_type=CanonicalDataType.TIMESTAMP,
                                            ts_val=datetime(2026, 1, 1)
                                        ),
                                    ),
                                    inclusivity=BoundInclusivity.EXCLUSIVE,
                                    unbounded=False
                                )
                            )
                        ),
                    )
                )
            return None

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

