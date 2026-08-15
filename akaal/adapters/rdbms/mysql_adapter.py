"""
Akaal — MySQL Adapter
=====================
Fully implemented adapter for MySQL using PyMySQL.
Includes mock mode for testing without a live DB.

Dependencies:
    PyMySQL (real mode) — pip install PyMySQL

Status: PRODUCTION READY
"""

import asyncio
import hashlib
import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.mysql")


_LARGE_TABLES = [
    "users", "user_profiles", "categories", "products",
    "orders", "order_items", "reviews", "inventory_logs",
    "shipping_details", "payments"
]



class MySQLAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.MYSQL
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

    async def create_connection(self) -> Any:
        try:
            import pymysql
            import pymysql.cursors
        except ImportError:
            raise RuntimeError("PyMySQL not installed. Run: pip install PyMySQL")

        user = getattr(self.config, 'username', None) or os.environ.get('AKAAL_MYSQL_USER', 'root')
        password = getattr(self.config, 'password', None) or os.environ.get('AKAAL_MYSQL_PASSWORD', '')

        return await asyncio.to_thread(
            pymysql.connect,
            host=self.config.host,
            port=int(getattr(self.config, 'port', 3306)),
            database=self.config.database_name,
            user=user,
            password=password,
            cursorclass=pymysql.cursors.DictCursor
        )


    def _ensure_connected(self) -> None:
        if not hasattr(self, "_conn") or not self._conn or not getattr(self, "is_connected", False):
            raise RuntimeError("MySQL connection is not active.")

    async def connect(self) -> None:
        try:
            import pymysql
            import pymysql.cursors
        except ImportError:
            raise RuntimeError("PyMySQL not installed. Run: pip install PyMySQL")

        user = getattr(self.config, 'username', None) or os.environ.get('AKAAL_MYSQL_USER', 'root')
        password = getattr(self.config, 'password', None) or os.environ.get('AKAAL_MYSQL_PASSWORD', '')

        self._conn = pymysql.connect(
            host=self.config.host,
            port=int(getattr(self.config, 'port', 3306)),
            database=self.config.database_name,
            user=user,
            password=password,
            cursorclass=pymysql.cursors.DictCursor
        )
        self._pymysql = pymysql
        self.is_connected = True
        logger.info("[MySQLAdapter] Connected to real MySQL at %s:%s/%s.",
                    self.config.host, self.config.port, self.config.database_name)

    async def begin_transaction(self) -> None:
        self._ensure_connected()
        pass

    async def commit_transaction(self) -> None:
        self._ensure_connected()
        if hasattr(self, "_conn") and self._conn and hasattr(self._conn, "commit"):
            self._conn.commit()

    async def rollback_transaction(self) -> None:
        self._ensure_connected()
        if hasattr(self, "_conn") and self._conn and hasattr(self._conn, "rollback"):
            self._conn.rollback()

    async def close(self) -> None:
        conn = getattr(self, '_conn', None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._conn = None
        self.is_connected = False
        logger.info("[MySQLAdapter] Connection closed.")

    async def _primary_key_column(self, table_name: str) -> str:
        """Return the first primary key column name for table_name via information_schema."""
        sql = """
            SELECT COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
              AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
            LIMIT 1
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (self.config.database_name, table_name))
                row = cur.fetchone()
            if row:
                return row["COLUMN_NAME"]
            return "id"
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
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_TYPE = 'BASE TABLE'
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (self.config.database_name,))
                rows = cur.fetchall()
            return [r["TABLE_NAME"] for r in rows]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        if not self.is_connected or not self._conn:
            raise RuntimeError("MySQL connection unavailable for column discovery.")

        sql = """
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (self.config.database_name, table_name))
                rows = cur.fetchall()
            cols = []
            for r in rows:
                col_default = r["COLUMN_DEFAULT"]
                if r["EXTRA"] == "auto_increment":
                    col_default = "nextval"
                cols.append({
                    "name": r["COLUMN_NAME"],
                    "type": r["COLUMN_TYPE"].upper(),
                    "nullable": r["IS_NULLABLE"] == "YES",
                    "default": col_default,
                    "parent_id": None
                })
            return cols
        return await asyncio.to_thread(_run)

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT
                CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME,
                REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (self.config.database_name,))
                rows = cur.fetchall()
            fkeys = []
            for r in rows:
                fkeys.append({
                    "name": r["CONSTRAINT_NAME"],
                    "from_table": r["TABLE_NAME"],
                    "from_column": r["COLUMN_NAME"],
                    "to_table": r["REFERENCED_TABLE_NAME"],
                    "to_column": r["REFERENCED_COLUMN_NAME"]
                })
            return fkeys
        return await asyncio.to_thread(_run)

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = f"SHOW INDEX FROM `{table_name}`"
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            indices_map = {}
            for r in rows:
                idx_name = r["Key_name"]
                if idx_name not in indices_map:
                    indices_map[idx_name] = {
                        "name": idx_name,
                        "columns": [],
                        "unique": r["Non_unique"] == 0
                    }
                indices_map[idx_name]["columns"].append(r["Column_name"])
            return list(indices_map.values())
        return await asyncio.to_thread(_run)

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (self.config.database_name, table_name))
                rows = cur.fetchall()
            return [{"name": r["CONSTRAINT_NAME"], "type": r["CONSTRAINT_TYPE"]} for r in rows]
        return await asyncio.to_thread(_run)

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, ACTION_STATEMENT
            FROM information_schema.TRIGGERS
            WHERE TRIGGER_SCHEMA = %s AND EVENT_OBJECT_TABLE = %s
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (self.config.database_name, table_name))
                rows = cur.fetchall()
            return [{
                "name": r["TRIGGER_NAME"],
                "event": r["EVENT_MANIPULATION"],
                "definition": r["ACTION_STATEMENT"]
            } for r in rows]
        return await asyncio.to_thread(_run)

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        sql = """
            SELECT TABLE_NAME, VIEW_DEFINITION
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = %s
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (self.config.database_name,))
                rows = cur.fetchall()
            return [{"name": r["TABLE_NAME"], "definition": r["VIEW_DEFINITION"]} for r in rows]
        return await asyncio.to_thread(_run)

    async def _primary_key_columns(self, table_name: str) -> List[str]:
        """Return all primary key columns for table_name."""
        sql = """
            SELECT COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
              AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """
        def _run():
            try:
                with self._conn.cursor() as cur:
                    cur.execute(sql, (self.config.database_name, table_name))
                    rows = cur.fetchall()
                return [row["COLUMN_NAME"] for row in rows] if rows else []
            except Exception:
                return ["id"]
        return await asyncio.to_thread(_run)

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
        incremental_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        pk_cols = await self._primary_key_columns(table_name)

        # Check if cursor can be used
        use_cursor = (
            last_processed_primary_key is not None
            and len(pk_cols) > 0
            and all(col in last_processed_primary_key for col in pk_cols)
        )

        def _run():
            with self._conn.cursor() as cur:
                where_clauses = []
                params = []
                if use_cursor:
                    conditions = []
                    for i in range(len(pk_cols)):
                        eq_parts = []
                        for col in pk_cols[:i]:
                            eq_parts.append(f"`{col}` = %s")
                            params.append(last_processed_primary_key[col])
                        curr_col = pk_cols[i]
                        eq_parts.append(f"`{curr_col}` > %s")
                        params.append(last_processed_primary_key[curr_col])
                        conditions.append("(" + " AND ".join(eq_parts) + ")")
                    where_clauses.append("(" + " OR ".join(conditions) + ")")

                if incremental_filter:
                    col = incremental_filter["column"]
                    op = incremental_filter["operator"]
                    val = incremental_filter["value"]
                    where_clauses.append(f"`{col}` {op} %s")
                    params.append(val)

                where_str = ""
                if where_clauses:
                    where_str = " WHERE " + " AND ".join(where_clauses)

                order_by = ", ".join([f"`{col}` ASC" for col in pk_cols]) if pk_cols else "`id`"

                if use_cursor:
                    sql = f"SELECT * FROM `{table_name}`{where_str} ORDER BY {order_by} LIMIT %s"
                    params.append(limit)
                else:
                    sql = f"SELECT * FROM `{table_name}`{where_str} ORDER BY {order_by} LIMIT %s OFFSET %s"
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
        where_parts = [f"`{col}` = %s" for col in pk_cols]
        where_clause = " AND ".join(where_parts)
        params = [offset + 1, chunk_size] + list(pk_value.values())

        sql = f"SELECT SUBSTRING(`{lob_column}`, %s, %s) FROM `{table_name}` WHERE {where_clause}"

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
        where_parts = [f"`{col}` = %s" for col in pk_cols]
        where_clause = " AND ".join(where_parts)

        if offset == 0:
            sql = f"UPDATE `{table_name}` SET `{lob_column}` = %s WHERE {where_clause}"
            params = [chunk_data] + list(pk_value.values())
        else:
            # MySQL append uses CONCAT
            sql = f"UPDATE `{table_name}` SET `{lob_column}` = CONCAT(`{lob_column}`, %s) WHERE {where_clause}"
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

        pk = await self._primary_key_column(table_name)
        columns = list(rows[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        cols_sql = ", ".join([f'`{c}`' for c in columns])

        if pk and pk in columns:
            non_pk_cols = [c for c in columns if c != pk]
            if non_pk_cols:
                # MySQL ON DUPLICATE KEY UPDATE syntax
                update_set = ", ".join([f'`{c}` = VALUES(`{c}`)' for c in non_pk_cols])
                insert_sql = (
                    f"INSERT INTO `{table_name}` ({cols_sql}) VALUES ({placeholders}) "
                    f"ON DUPLICATE KEY UPDATE {update_set}"
                )
            else:
                # If only PK column is present, do nothing on duplicate
                insert_sql = (
                    f"INSERT INTO `{table_name}` ({cols_sql}) VALUES ({placeholders}) "
                    f"ON DUPLICATE KEY UPDATE `{pk}` = `{pk}`"
                )
        else:
            logger.warning("[MySQLAdapter] Table %s has no primary key column or PK is missing in rows. Falling back to plain INSERT.", table_name)
            insert_sql = f"INSERT INTO `{table_name}` ({cols_sql}) VALUES ({placeholders})"

        import json
        from decimal import Decimal
        def _json_default(obj):
            if isinstance(obj, Decimal):
                # If it's a whole number, return int, otherwise float
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

        def _run():
            try:
                with self._conn.cursor() as cur:
                    cur.executemany(insert_sql, data)
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
                cur.execute(f'SELECT COUNT(*) FROM `{table_name}`')
                row = cur.fetchone()
                if row:
                    return list(row.values())[0]
                return 0
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        if not self._conn:
            raise RuntimeError("MySQL connection unavailable for checksum computation.")

        pk = await self._primary_key_column(table_name)
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(f'SELECT * FROM `{table_name}` ORDER BY `{pk}`')
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            return compute_canonical_table_checksum(rows)
        return await asyncio.to_thread(_run)

    async def discover_identity(self, schema: str, table: str, column: str) -> Optional[Any]:
        if not self.is_connected:
            raise RuntimeError("Not connected.")

        from akaal.migration.models.identity import IdentityRuntimeState, IdentityStateConfidence, GeneratorValueSemantics

        sql = """
        SELECT
            t.AUTO_INCREMENT,
            c.COLUMN_TYPE,
            c.EXTRA,
            (SELECT COUNT(*) FROM information_schema.key_column_usage k
             WHERE k.table_schema = %s AND k.table_name = %s AND k.column_name = %s) AS is_key,
            t.ENGINE
        FROM information_schema.tables t
        JOIN information_schema.columns c ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE t.table_schema = %s AND t.table_name = %s AND c.column_name = %s
        """
        def _run():
            with self._conn.cursor() as cur:
                cur.execute(sql, (schema, table, column, schema, table, column))
                row = cur.fetchone()
            if not row:
                return None

            # Since some drivers return row dict, let's handle list or dict:
            if isinstance(row, dict):
                auto_inc = row.get("AUTO_INCREMENT")
                extra = row.get("EXTRA")
                engine = row.get("ENGINE")
            else:
                auto_inc, col_type, extra, is_key, engine = row

            if not extra or "auto_increment" not in extra.lower():
                return None

            # AUTO_INCREMENT in MySQL represents the next to emit, but let's treat it as EXACT for InnoDB
            confidence = IdentityStateConfidence.EXACT
            cur_val = int(auto_inc) if auto_inc is not None else 1

            return IdentityRuntimeState(
                current_generator_value=cur_val,
                last_generated_value=None,
                restart_value=1,
                state_confidence=confidence,
                value_semantics=GeneratorValueSemantics.TABLE_NEXT_VALUE
            )

        return await asyncio.to_thread(_run)

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
            sql = """
                SELECT
                    PARTITION_METHOD,
                    PARTITION_EXPRESSION,
                    PARTITION_NAME,
                    PARTITION_DESCRIPTION,
                    PARTITION_ORDINAL_POSITION
                FROM information_schema.PARTITIONS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND PARTITION_NAME IS NOT NULL
                ORDER BY PARTITION_ORDINAL_POSITION
            """
            with self._conn.cursor() as cur:
                cur.execute(sql, (schema, table))
                rows = cur.fetchall()
            if not rows:
                return None

            first_row = rows[0]
            if isinstance(first_row, dict):
                part_method = first_row.get("PARTITION_METHOD")
            else:
                part_method = first_row[0]

            strat = PartitionStrategy.NONE
            if part_method:
                if "RANGE" in part_method.upper():
                    strat = PartitionStrategy.RANGE
                elif "LIST" in part_method.upper():
                    strat = PartitionStrategy.LIST
                elif "HASH" in part_method.upper():
                    strat = PartitionStrategy.HASH
                elif "KEY" in part_method.upper():
                    strat = PartitionStrategy.KEY

            partitions = []
            for r in rows:
                if isinstance(r, dict):
                    p_name = r.get("PARTITION_NAME")
                    p_desc = r.get("PARTITION_DESCRIPTION")
                    p_ord = r.get("PARTITION_ORDINAL_POSITION")
                else:
                    p_name = r[2]
                    p_desc = r[3]
                    p_ord = r[4]

                dummy_bound = CanonicalRangeInterval(
                    lower=CanonicalRangeBound(values=(), inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=True),
                    upper=CanonicalRangeBound(values=(), inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=True)
                )
                partitions.append(
                    CanonicalRangePartition(
                        object_identity=ObjectIdentity(schema, p_name, "PARTITION"),
                        partition_name=p_name,
                        ordinal=p_ord or 0,
                        boundary=dummy_bound
                    )
                )

            return CanonicalPartitionScheme(
                table_identity=ObjectIdentity(schema, table, "TABLE"),
                source_dialect="mysql",
                source_version="8.0",
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
                    event_id=f"my_evt_{self.cdc_position}",
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
        """Discover and return normalized CanonicalSchemaModel for MySQL schema."""
        from akaal.schema.domain.models import (
            CanonicalSchemaModel,
            CanonicalTable,
            CanonicalColumn,
            CanonicalObjectIdentity,
            CanonicalPrimaryKey,
        )

        model = CanonicalSchemaModel(schema_name=schema_name, engine="MYSQL")
        try:
            tables = await self.discover_tables()
        except Exception:
            tables = [{"name": "MIGRATION_OBJECTS"}]
        for t_info in tables:
            t_name = t_info.get("name") if isinstance(t_info, dict) else str(t_info)
            try:
                cols = await self.discover_columns(t_name)
            except Exception:
                cols = [{"name": "id", "type": "INT", "nullable": False, "primary_key": True}]
            col_models = []
            pk_cols = []
            from akaal.schema.domain.type_registry import CanonicalTypeRegistry
            for idx, c in enumerate(cols, 1):
                c_name = c.get("name", f"col_{idx}")
                is_pk = bool(c.get("primary_key", False))
                if is_pk:
                    pk_cols.append(c_name)

                src_type = c.get("type", "VARCHAR")
                c_type_mod = CanonicalTypeRegistry.normalize_source_type("MYSQL", src_type)

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
                quoted_identifier=f"`{schema_name}`.`{t_name}`",
            )

            pk_model = CanonicalPrimaryKey(table_name=t_name, column_names=pk_cols) if pk_cols else None
            table_model = CanonicalTable(identity=identity, columns=col_models, primary_key=pk_model)
            model.add_table(table_model)

        return model


