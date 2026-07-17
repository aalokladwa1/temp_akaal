"""
Akaal — SQLite Adapter
======================
Implements BaseAdapter for SQLite using standard sqlite3 wrapped in threads.
"""

import asyncio
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.sqliteadapter")


class SQLiteAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.SQLITE
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.BULK_WRITE,
        AdapterCapability.TRANSACTION_SUPPORT
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._conn = None
        self._db_path = getattr(config, "database_name", ":memory:")
        if isinstance(config, dict):
            self._db_path = config.get("database_name") or config.get("db_path") or ":memory:"

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def create_connection(self) -> Any:
        if self.mock_mode:
            return "mock_sqlite_conn"
        def _connect():
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        return await asyncio.to_thread(_connect)

    async def close_connection(self, conn: Any) -> None:
        if conn and conn != "mock_sqlite_conn":
            def _close():
                conn.close()
            await asyncio.to_thread(_close)

    async def validate_connection(self, conn: Any) -> bool:
        if conn == "mock_sqlite_conn":
            return True
        if conn is None:
            return False
        try:
            def _val():
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
            await asyncio.to_thread(_val)
            return True
        except Exception:
            return False

    async def connect(self) -> None:
        """Connect to SQLite database."""
        self._conn = await self.create_connection()
        self.is_connected = True
        logger.info("[SQLiteAdapter] Connected to DB at %s", self._db_path)

    async def close(self) -> None:
        """Close SQLite connection."""
        if self._conn:
            await self.close_connection(self._conn)
            self._conn = None
        self.is_connected = False
        logger.info("[SQLiteAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Schema Discovery stubs / mocks
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        if self.mock_mode:
            return ["users", "orders", "composite_table"]
        
        def _get_tables():
            cursor = self._conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            return [row["name"] for row in cursor.fetchall()]
        return await asyncio.to_thread(_get_tables)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return [{"name": "id", "type": "INTEGER", "nullable": False, "default": None}]
            
        def _get_cols():
            cursor = self._conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            cols = []
            for row in cursor.fetchall():
                cols.append({
                    "name": row["name"],
                    "type": row["type"],
                    "nullable": not row["notnull"],
                    "default": row["dflt_value"]
                })
            return cols
        return await asyncio.to_thread(_get_cols)

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

        def _get_pks():
            cursor = self._conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            rows = cursor.fetchall()
            # pk field is > 0 if it is part of primary key. Sort by it to preserve PK order.
            pk_rows = [row for row in rows if row["pk"] > 0]
            pk_rows.sort(key=lambda r: r["pk"])
            return [row["name"] for row in pk_rows]
        return await asyncio.to_thread(_get_pks)

    async def _primary_key_column(self, table_name: str) -> str:
        pks = await self._primary_key_columns(table_name)
        return pks[0] if pks else "id"

    # ------------------------------------------------------------------
    # Data Operations
    # ------------------------------------------------------------------

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
        incremental_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if self.mock_mode:
            start_id = offset
            pk_cols = await self._primary_key_columns(table_name)
            if last_processed_primary_key and pk_cols:
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
            if start_id + limit > 250:
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
                elif table_name == "lob_table":
                    row["id"] = i
                    row["blob_col"] = f"mock_blob_value_{i}"
                else:
                    row["id"] = i
                rows.append(row)
            return rows

        pk_cols = await self._primary_key_columns(table_name)
        use_cursor = (
            last_processed_primary_key is not None 
            and len(pk_cols) > 0 
            and all(col in last_processed_primary_key for col in pk_cols)
        )

        def _run():
            cursor = self._conn.cursor()
            try:
                where_clauses = []
                params = []
                if use_cursor:
                    conditions = []
                    for i in range(len(pk_cols)):
                        eq_parts = []
                        for col in pk_cols[:i]:
                            eq_parts.append(f'"{col}" = ?')
                            params.append(last_processed_primary_key[col])
                        curr_col = pk_cols[i]
                        eq_parts.append(f'"{curr_col}" > ?')
                        params.append(last_processed_primary_key[curr_col])
                        conditions.append("(" + " AND ".join(eq_parts) + ")")
                    where_clauses.append("(" + " OR ".join(conditions) + ")")

                if incremental_filter:
                    col = incremental_filter["column"]
                    op = incremental_filter["operator"]
                    val = incremental_filter["value"]
                    where_clauses.append(f'"{col}" {op} ?')
                    params.append(val)

                where_str = ""
                if where_clauses:
                    where_str = " WHERE " + " AND ".join(where_clauses)

                order_by = ", ".join([f'"{col}" ASC' for col in pk_cols]) if pk_cols else '"id"'
                
                if use_cursor:
                    sql = f'SELECT * FROM "{table_name}"{where_str} ORDER BY {order_by} LIMIT ?'
                    params.append(limit)
                else:
                    sql = f'SELECT * FROM "{table_name}"{where_str} ORDER BY {order_by} LIMIT ? OFFSET ?'
                    params.append(limit)
                    params.append(offset)

                cursor.execute(sql, tuple(params))
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, row)) for row in cursor.fetchall()]
            finally:
                cursor.close()

        return await asyncio.to_thread(_run)

    async def read_lob_chunk(
        self,
        table_name: str,
        pk_value: Dict[str, Any],
        lob_column: str,
        offset: int,
        chunk_size: int,
    ) -> bytes:
        if self.mock_mode:
            mock_data = f"mock_lob_data_for_row_{list(pk_value.values())[0] if pk_value else 0}".encode()
            return mock_data[offset : offset + chunk_size]

        pk_cols = list(pk_value.keys())
        where_parts = [f'"{col}" = ?' for col in pk_cols]
        where_clause = " AND ".join(where_parts)
        # SQLite substr is 1-indexed
        params = [offset + 1, chunk_size] + list(pk_value.values())

        sql = f'SELECT substr("{lob_column}", ?, ?) FROM "{table_name}" WHERE {where_clause}'

        def _run():
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql, tuple(params))
                row = cursor.fetchone()
                return bytes(row[0]) if row and row[0] is not None else b""
            finally:
                cursor.close()
        return await asyncio.to_thread(_run)

    async def write_lob_chunk(
        self,
        table_name: str,
        pk_value: Dict[str, Any],
        lob_column: str,
        chunk_data: bytes,
        offset: int,
    ) -> None:
        if self.mock_mode:
            return

        pk_cols = list(pk_value.keys())
        where_parts = [f'"{col}" = ?' for col in pk_cols]
        where_clause = " AND ".join(where_parts)

        if offset == 0:
            sql = f'UPDATE "{table_name}" SET "{lob_column}" = ? WHERE {where_clause}'
            params = [chunk_data] + list(pk_value.values())
        else:
            # SQLite uses || operator
            sql = f'UPDATE "{table_name}" SET "{lob_column}" = "{lob_column}" || ? WHERE {where_clause}'
            params = [chunk_data] + list(pk_value.values())

        def _run():
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql, tuple(params))
                self._conn.commit()
            finally:
                cursor.close()
        await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        if self.mock_mode:
            return len(rows)
        if not rows:
            return 0

        def _write():
            cursor = self._conn.cursor()
            try:
                columns = list(rows[0].keys())
                placeholders = ", ".join(["?"] * len(columns))
                cols_sql = ", ".join([f'"{c}"' for c in columns])
                sql = f'INSERT OR REPLACE INTO "{table_name}" ({cols_sql}) VALUES ({placeholders})'
                
                vals = [tuple(row[c] for c in columns) for row in rows]
                cursor.executemany(sql, vals)
                self._conn.commit()
                return cursor.rowcount
            finally:
                cursor.close()
        return await asyncio.to_thread(_write)

    async def get_row_count(self, table_name: str) -> int:
        if self.mock_mode:
            return 250
        def _count():
            cursor = self._conn.cursor()
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                return cursor.fetchone()[0]
            finally:
                cursor.close()
        return await asyncio.to_thread(_count)

    async def compute_checksum(self, table_name: str) -> str:
        return "mock_checksum"

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        return []

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    async def discover_views(self) -> List[Dict[str, Any]]:
        return []
