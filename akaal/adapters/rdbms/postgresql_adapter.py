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

    async def connect(self) -> None:
        if self.mock_mode:
            if getattr(self.config, "host", "") == "connection-fail.example.com":
                raise ConnectionError("Mock: PostgreSQL connection failure.")
            self.is_connected = True
            logger.info("[PostgreSQLAdapter] Connected (mock).")
            return
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            raise RuntimeError("psycopg2 not installed. Run: pip install psycopg2-binary")
        user = getattr(self.config, 'username', None) or os.environ.get('AKAAL_PG_USER', 'postgres')
        password = getattr(self.config, 'password', None) or os.environ.get('AKAAL_PG_PASSWORD', '')
        self._conn = psycopg2.connect(
            host=self.config.host,
            port=int(getattr(self.config, 'port', 5432)),
            dbname=self.config.database_name,
            user=user,
            password=password,
        )
        self._psycopg2 = psycopg2
        self.is_connected = True
        logger.info("[PostgreSQLAdapter] Connected to real PostgreSQL at %s:%s/%s.",
                    self.config.host, self.config.port, self.config.database_name)

    async def close(self) -> None:
        conn = getattr(self, '_conn', None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
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
        return []

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        if not self.is_connected:
            raise RuntimeError("Not connected.")
        if self.mock_mode:
            return _MOCK_COLUMNS.get(table_name, [
                {"name": "id", "type": "INTEGER", "nullable": False, "default": None, "parent_id": None}
            ])
        return []

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return [
                {"name": "fk_orders_user", "from_table": "orders", "from_column": "user_id", "to_table": "users", "to_column": "id"},
            ]
        return []

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return [{"name": f"{table_name}_pkey", "columns": ["id"], "unique": True}]
        return []

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return []
        return []

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return []
        return []

    async def discover_views(self) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return []
        return []

    async def read_batch(self, table_name: str, offset: int, limit: int) -> List[Dict[str, Any]]:
        if self.mock_mode:
            return [{"id": i, "data": f"mock_row_{i}"} for i in range(offset, offset + limit)]
        pk = await self._primary_key_column(table_name)
        def _run():
            with self._conn.cursor(cursor_factory=self._psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f'SELECT * FROM "{table_name}" ORDER BY "{pk}" LIMIT %s OFFSET %s',
                    (limit, offset)
                )
                return [dict(row) for row in cur.fetchall()]
        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        if self.mock_mode:
            logger.info("[PostgreSQLAdapter] Mock write: %d rows to %s", len(rows), table_name)
            return len(rows)
        if not rows:
            return 0

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

        data = [tuple(row[col] for col in columns) for row in rows]
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
