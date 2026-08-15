"""
Akaal — MariaDB Adapter (P4.2 Physical Reality)
================================================
Physical BaseAdapter implementation for MariaDB using PyMySQL/MariaDB driver.
Strict Zero-Fake Policy: Requires physical MariaDB database connection.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.mariadb")


class MariaDBAdapter(BaseAdapter):
    """
    Production-grade adapter for MariaDB.
    Provides schema discovery, batch read/write, transaction primitives, and CDC metadata hooks.
    """

    SYSTEM_TYPE = SystemType.MARIADB
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.BULK_WRITE,
        AdapterCapability.CDC_SUPPORT,
        AdapterCapability.TRANSACTION_SUPPORT,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._client = None
        self._in_transaction = False

    def _ensure_connected(self) -> None:
        if not self._client or not self.is_connected:
            raise RuntimeError("MariaDB connection is not active.")

    async def connect(self) -> None:
        """Establishes physical connection to MariaDB server."""
        try:
            import pymysql
        except ImportError as exc:
            self.is_connected = False
            raise RuntimeError("MariaDB physical driver 'pymysql' is not installed.") from exc

        try:
            host = getattr(self.config, "host", "") or "localhost"
            port = getattr(self.config, "port", 3306) or 3306
            db_name = getattr(self.config, "database_name", "") or ""
            extra = getattr(self.config, "extra", {}) or {}
            username = extra.get("username", getattr(self.config, "username", ""))
            password = extra.get("password", getattr(self.config, "password", ""))

            self._client = pymysql.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=db_name,
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
            )
            self.is_connected = True
            logger.info(f"[MariaDBAdapter] Connected to physical MariaDB at {host}:{port}.")
        except Exception as exc:
            self.is_connected = False
            self._client = None
            logger.error(f"[MariaDBAdapter] Physical connection failed: {exc}")
            raise RuntimeError(f"Failed to connect to physical MariaDB database: {exc}") from exc

    async def close(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self.is_connected = False
        self._in_transaction = False
        logger.info("[MariaDBAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        try:
            with self._client.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False

    async def get_server_version(self) -> str:
        self._ensure_connected()
        with self._client.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            res = cursor.fetchone()
            return str(list(res.values())[0]) if res else "MariaDB"

    # ------------------------------------------------------------------
    # Schema Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        db_name = getattr(self.config, "database_name", "")
        with self._client.cursor() as cursor:
            cursor.execute(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
                (db_name,)
            )
            rows = cursor.fetchall()
            return [r["TABLE_NAME"] for r in rows]

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        db_name = getattr(self.config, "database_name", "")
        with self._client.cursor() as cursor:
            cursor.execute(
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION",
                (db_name, table_name)
            )
            rows = cursor.fetchall()
            return [{
                "name": r["COLUMN_NAME"],
                "type": str(r["DATA_TYPE"]).upper(),
                "nullable": r["IS_NULLABLE"].upper() == "YES",
                "default": r["COLUMN_DEFAULT"],
            } for r in rows]

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        db_name = getattr(self.config, "database_name", "")
        with self._client.cursor() as cursor:
            cursor.execute(
                "SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
                "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL",
                (db_name,)
            )
            rows = cursor.fetchall()
            return [{
                "constraint_name": r["CONSTRAINT_NAME"],
                "table_name": r["TABLE_NAME"],
                "column_name": r["COLUMN_NAME"],
                "foreign_table_name": r["REFERENCED_TABLE_NAME"],
                "foreign_column_name": r["REFERENCED_COLUMN_NAME"],
            } for r in rows]

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        db_name = getattr(self.config, "database_name", "")
        with self._client.cursor() as cursor:
            cursor.execute(
                "SELECT INDEX_NAME, NON_UNIQUE, COLUMN_NAME FROM INFORMATION_SCHEMA.STATISTICS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY INDEX_NAME, SEQ_IN_INDEX",
                (db_name, table_name)
            )
            rows = cursor.fetchall()
            idx_map: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                name = r["INDEX_NAME"]
                if name not in idx_map:
                    idx_map[name] = {"name": name, "unique": r["NON_UNIQUE"] == 0, "columns": []}
                idx_map[name]["columns"].append(r["COLUMN_NAME"])
            return list(idx_map.values())

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        db_name = getattr(self.config, "database_name", "")
        with self._client.cursor() as cursor:
            cursor.execute(
                "SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                (db_name, table_name)
            )
            rows = cursor.fetchall()
            return [{"name": r["CONSTRAINT_NAME"], "type": r["CONSTRAINT_TYPE"]} for r in rows]

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        db_name = getattr(self.config, "database_name", "")
        with self._client.cursor() as cursor:
            cursor.execute(
                "SELECT TRIGGER_NAME, ACTION_STATEMENT FROM INFORMATION_SCHEMA.TRIGGERS "
                "WHERE EVENT_OBJECT_SCHEMA = %s AND EVENT_OBJECT_TABLE = %s",
                (db_name, table_name)
            )
            rows = cursor.fetchall()
            return [{"name": r["TRIGGER_NAME"], "statement": r["ACTION_STATEMENT"]} for r in rows]

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        db_name = getattr(self.config, "database_name", "")
        with self._client.cursor() as cursor:
            cursor.execute(
                "SELECT TABLE_NAME, VIEW_DEFINITION FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = %s",
                (db_name,)
            )
            rows = cursor.fetchall()
            return [{"name": r["TABLE_NAME"], "definition": r["VIEW_DEFINITION"]} for r in rows]

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
        sql = f"SELECT * FROM `{table_name}` LIMIT %s OFFSET %s"
        with self._client.cursor() as cursor:
            cursor.execute(sql, (limit, offset))
            return cursor.fetchall()

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        cols = list(rows[0].keys())
        cols_sql = ", ".join([f"`{c}`" for c in cols])
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO `{table_name}` ({cols_sql}) VALUES ({placeholders})"
        vals = [tuple(r.get(c) for c in cols) for r in rows]
        with self._client.cursor() as cursor:
            count = cursor.executemany(sql, vals)
            return count

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        sql = f"SELECT COUNT(*) AS cnt FROM `{table_name}`"
        with self._client.cursor() as cursor:
            cursor.execute(sql)
            res = cursor.fetchone()
            return int(res["cnt"]) if res else 0

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        sql = f"SELECT * FROM `{table_name}`"
        with self._client.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return compute_canonical_table_checksum(rows, order_independent=True)

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def begin_transaction(self) -> None:
        self._ensure_connected()
        self._client.begin()
        self._in_transaction = True

    async def commit_transaction(self) -> None:
        self._ensure_connected()
        if self._in_transaction:
            self._client.commit()
            self._in_transaction = False

    async def rollback_transaction(self) -> None:
        self._ensure_connected()
        if self._in_transaction:
            self._client.rollback()
            self._in_transaction = False
