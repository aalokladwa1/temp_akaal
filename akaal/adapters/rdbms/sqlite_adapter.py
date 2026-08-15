"""
Akaal — SQLite Adapter (P4.2 Physical Reality)
================================================
Physical BaseAdapter implementation for SQLite using standard sqlite3.
Strict Zero-Fake Policy: Requires physical database connection/file.
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
        AdapterCapability.TRANSACTION_SUPPORT,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._conn: Optional[sqlite3.Connection] = None
        self._in_transaction = False
        self._db_path = getattr(config, "database_name", ":memory:")
        if isinstance(config, dict):
            self._db_path = config.get("database_name") or config.get("db_path") or ":memory:"

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def create_connection(self) -> sqlite3.Connection:
        import os
        if not self._db_path:
            raise ValueError("SQLite database_name / path is required.")
        if self._db_path != ":memory:" and not self._db_path.startswith("file:"):
            parent_dir = os.path.dirname(self._db_path)
            if parent_dir and not os.path.exists(parent_dir):
                raise FileNotFoundError(f"Directory for SQLite database file does not exist: '{parent_dir}'")
        def _connect():
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        return await asyncio.to_thread(_connect)

    async def close_connection(self, conn: sqlite3.Connection) -> None:
        if conn:
            def _close():
                try:
                    conn.close()
                except Exception:
                    pass
            await asyncio.to_thread(_close)

    async def validate_connection(self, conn: sqlite3.Connection) -> bool:
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
        """Establishes physical connection to SQLite database file or memory."""
        self._conn = await self.create_connection()
        self.is_connected = True
        self._in_transaction = False
        logger.info("[SQLiteAdapter] Connected to DB at %s", self._db_path)

    async def close(self) -> None:
        """Close physical SQLite connection."""
        if self._conn:
            await self.close_connection(self._conn)
            self._conn = None
        self.is_connected = False
        self._in_transaction = False
        logger.info("[SQLiteAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        if not self._conn:
            raise RuntimeError("SQLite connection is not active.")
        return await self.validate_connection(self._conn)

    async def begin_transaction(self) -> None:
        if not self._conn:
            raise RuntimeError("SQLite connection is not active for transaction begin.")
        self._in_transaction = True

    async def commit_transaction(self) -> None:
        if not self._conn:
            raise RuntimeError("SQLite connection is not active for transaction commit.")
        def _run():
            self._conn.commit()
        await asyncio.to_thread(_run)
        self._in_transaction = False

    async def rollback_transaction(self) -> None:
        if not self._conn:
            raise RuntimeError("SQLite connection is not active for transaction rollback.")
        def _run():
            self._conn.rollback()
        await asyncio.to_thread(_run)
        self._in_transaction = False

    def _ensure_connected(self) -> None:
        if not self._conn:
            raise RuntimeError("SQLite connection is not active.")

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        def _get_tables():
            cursor = self._conn.cursor()
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                return [row["name"] for row in cursor.fetchall()]
            finally:
                cursor.close()
        return await asyncio.to_thread(_get_tables)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _get_cols():
            cursor = self._conn.cursor()
            try:
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                cols = []
                for row in cursor.fetchall():
                    cols.append({
                        "name": row["name"],
                        "type": row["type"],
                        "nullable": not row["notnull"],
                        "default": row["dflt_value"]
                    })
                return cols
            finally:
                cursor.close()
        return await asyncio.to_thread(_get_cols)

    async def _primary_key_columns(self, table_name: str) -> List[str]:
        self._ensure_connected()
        def _get_pks():
            cursor = self._conn.cursor()
            try:
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                rows = cursor.fetchall()
                pk_rows = [row for row in rows if row["pk"] > 0]
                pk_rows.sort(key=lambda r: r["pk"])
                return [row["name"] for row in pk_rows]
            finally:
                cursor.close()
        return await asyncio.to_thread(_get_pks)

    async def _primary_key_column(self, table_name: str) -> str:
        pks = await self._primary_key_columns(table_name)
        return pks[0] if pks else None

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
        self._ensure_connected()
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

                order_by = ", ".join([f'"{col}" ASC' for col in pk_cols]) if pk_cols else "ROWID"

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
        self._ensure_connected()
        pk_cols = list(pk_value.keys())
        where_parts = [f'"{col}" = ?' for col in pk_cols]
        where_clause = " AND ".join(where_parts)
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
        self._ensure_connected()
        pk_cols = list(pk_value.keys())
        where_parts = [f'"{col}" = ?' for col in pk_cols]
        where_clause = " AND ".join(where_parts)

        if offset == 0:
            sql = f'UPDATE "{table_name}" SET "{lob_column}" = ? WHERE {where_clause}'
            params = [chunk_data] + list(pk_value.values())
        else:
            sql = f'UPDATE "{table_name}" SET "{lob_column}" = "{lob_column}" || ? WHERE {where_clause}'
            params = [chunk_data] + list(pk_value.values())

        def _run():
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql, tuple(params))
                if not self._in_transaction:
                    self._conn.commit()
            finally:
                cursor.close()
        await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
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
                if not self._in_transaction:
                    self._conn.commit()
                return cursor.rowcount
            finally:
                cursor.close()
        return await asyncio.to_thread(_write)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        def _count():
            cursor = self._conn.cursor()
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                return cursor.fetchone()[0]
            except Exception as e:
                raise RuntimeError(f"SQLite row count query failed for '{table_name}': {e}") from e
            finally:
                cursor.close()
        return await asyncio.to_thread(_count)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        def _calc():
            cursor = self._conn.cursor()
            try:
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                cols_info = cursor.fetchall()
                pk_cols = [c[1] for c in cols_info if c[5] > 0]
                order_clause = f'ORDER BY {", ".join([f"""("{c}")""" for c in pk_cols])}' if pk_cols else ""

                cursor.execute(f'SELECT * FROM "{table_name}" {order_clause}')
                col_names = [d[0] for d in cursor.description] if cursor.description else []

                def _row_stream():
                    while True:
                        batch = cursor.fetchmany(1000)
                        if not batch:
                            break
                        for r in batch:
                            yield dict(zip(col_names, r))

                return compute_canonical_table_checksum(_row_stream(), order_independent=(not pk_cols))
            finally:
                cursor.close()
        return await asyncio.to_thread(_calc)

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        tables = await self.discover_tables()
        def _get_fks():
            fks = []
            cursor = self._conn.cursor()
            try:
                for tbl in tables:
                    cursor.execute(f'PRAGMA foreign_key_list("{tbl}")')
                    for row in cursor.fetchall():
                        fks.append({
                            "table_name": tbl,
                            "column_name": row["from"],
                            "foreign_table_name": row["table"],
                            "foreign_column_name": row["to"],
                            "constraint_name": f"fk_{tbl}_{row['from']}",
                        })
                return fks
            finally:
                cursor.close()
        return await asyncio.to_thread(_get_fks)

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _get_idx():
            indexes = []
            cursor = self._conn.cursor()
            try:
                cursor.execute(f'PRAGMA index_list("{table_name}")')
                for row in cursor.fetchall():
                    indexes.append({
                        "name": row["name"],
                        "unique": bool(row["unique"]),
                        "origin": row["origin"],
                    })
                return indexes
            finally:
                cursor.close()
        return await asyncio.to_thread(_get_idx)

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        pks = await self._primary_key_columns(table_name)
        constraints = []
        if pks:
            constraints.append({"name": f"pk_{table_name}", "type": "PRIMARY KEY", "columns": pks})
        return constraints

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _get_trig():
            cursor = self._conn.cursor()
            try:
                cursor.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
                    (table_name,)
                )
                return [{"name": row["name"], "sql": row["sql"]} for row in cursor.fetchall()]
            finally:
                cursor.close()
        return await asyncio.to_thread(_get_trig)

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _get_views():
            cursor = self._conn.cursor()
            try:
                cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='view'")
                return [{"name": row["name"], "definition": row["sql"]} for row in cursor.fetchall()]
            finally:
                cursor.close()
        return await asyncio.to_thread(_get_views)
