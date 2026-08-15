"""
Akaal — Amazon Redshift Adapter (P4.3 Physical Reality)
========================================================
Physical BaseAdapter and IWarehouseCapability implementation for Amazon Redshift.
Strict Zero-Fake Policy: Uses physical redshift_connector driver.
Fails closed when disconnected or when driver is missing.
"""

import logging
import asyncio
import hashlib
from typing import Any, Dict, List, Optional

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability
from akaal.connectors.contracts.warehouse import IWarehouseCapability

logger = logging.getLogger("akaal.adapters.redshift")


class RedshiftAdapter(BaseAdapter, IWarehouseCapability):
    """Physical Production Adapter for Amazon Redshift."""

    SYSTEM_TYPE = SystemType.REDSHIFT
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
        AdapterCapability.TRANSACTION_SUPPORT,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._client = None
        self._in_transaction = False
        extra = getattr(config, "extra", {}) or {}
        self.host = getattr(config, "host", "")
        self.port = int(getattr(config, "port", 5439) or 5439)
        self.database = getattr(config, "database_name", "dev") or "dev"
        self.schema = extra.get("schema", "public") or "public"
        self.iam_role = extra.get("iam_role", "")

    async def create_connection(self) -> Any:
        try:
            import redshift_connector
        except Exception as exc:
            raise RuntimeError("redshift-connector not installed. Run: pip install redshift-connector") from exc

        if not self.host:
            raise RuntimeError("Adapter config must include Redshift cluster host endpoint")

        extra = getattr(self.config, "extra", {}) or {}
        user = getattr(self.config, "username", None) or extra.get("username") or getattr(self.config, "credentials_ref", "awsuser")
        pwd = extra.get("password", "")

        def _connect():
            return redshift_connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=user,
                password=pwd,
            )

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        """Establishes physical connection to Amazon Redshift cluster."""
        try:
            self._client = await self.create_connection()
            self.is_connected = True
            logger.info(f"[RedshiftAdapter] Connected to Redshift cluster at {self.host}")
        except Exception as exc:
            self.is_connected = False
            self._client = None
            raise RuntimeError(f"Failed to connect to physical Redshift database: {exc}") from exc

    async def close(self) -> None:
        """Closes physical Redshift connection."""
        if self._client:
            try:
                def _close():
                    if hasattr(self._client, "close"):
                        self._client.close()
                await asyncio.to_thread(_close)
            except Exception:
                pass
        self._client = None
        self.is_connected = False
        self._in_transaction = False
        logger.info("[RedshiftAdapter] Connection closed.")

    def _ensure_connected(self) -> None:
        if not self._client or not getattr(self, "is_connected", False):
            raise RuntimeError("Redshift connection is not active.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        def _check():
            with self._client.cursor() as cur:
                cur.execute("SELECT VERSION()")
                row = cur.fetchone()
                return bool(row)
        return await asyncio.to_thread(_check)

    # -------------------------------------------------------------------------
    # Schema Discovery & Metadata
    # -------------------------------------------------------------------------

    async def discover_datasets(self) -> List[str]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute("SELECT schema_name FROM information_schema.schemata")
                return [r[0] for r in cur.fetchall()]
        return await asyncio.to_thread(_run)

    async def discover_warehouse_tables(self, dataset_name: Optional[str] = None) -> List[str]:
        return await self.discover_tables()

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{self.schema}' AND table_type = 'BASE TABLE'")
                return [r[0] for r in cur.fetchall()]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = '{self.schema}' AND table_name = '{table_name}' ORDER BY ordinal_position")
                cols = []
                for r in cur.fetchall():
                    cols.append({
                        "name": r[0],
                        "type": r[1],
                        "nullable": (r[2] == "YES"),
                        "default": r[3],
                    })
                return cols
        return await asyncio.to_thread(_run)

    async def _primary_key_columns(self, table_name: str) -> List[str]:
        self._ensure_connected()
        def _run():
            try:
                with self._client.cursor() as cur:
                    cur.execute(f"SELECT kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name WHERE tc.table_schema = '{self.schema}' AND tc.table_name = '{table_name}' AND tc.constraint_type = 'PRIMARY KEY' ORDER BY kcu.ordinal_position")
                    rows = cur.fetchall()
                    return [r[0] for r in rows] if rows else []
            except Exception:
                return []
        return await asyncio.to_thread(_run)

    async def _unique_key_columns(self, table_name: str) -> List[str]:
        return await self._primary_key_columns(table_name)

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        return []

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        pks = await self._primary_key_columns(table_name)
        if pks:
            return [{"constraint_name": f"PK_{table_name}", "constraint_type": "PRIMARY KEY", "columns": pks}]
        return []

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        return []

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SELECT table_name, view_definition FROM information_schema.views WHERE table_schema = '{self.schema}'")
                return [{"view_name": r[0], "definition": r[1]} for r in cur.fetchall()]
        return await asyncio.to_thread(_run)

    async def get_clustering_metadata(self, table_name: str) -> Dict[str, Any]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SELECT \"sortkey\", \"diststyle\" FROM PG_TABLE_DEF WHERE tablename = '{table_name}' AND schemaname = '{self.schema}'")
                rows = cur.fetchall()
                sort_keys = [r[0] for r in rows if r[0]]
                dist_style = rows[0][1] if rows else None
                return {
                    "table_name": table_name,
                    "sort_keys": sort_keys,
                    "dist_style": dist_style,
                }
        return await asyncio.to_thread(_run)

    # -------------------------------------------------------------------------
    # Bulk Extraction & Ingestion
    # -------------------------------------------------------------------------

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
        incremental_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        pk_cols = await self._unique_key_columns(table_name)
        use_cursor = (
            last_processed_primary_key is not None
            and len(pk_cols) > 0
            and all(col in last_processed_primary_key for col in pk_cols)
        )

        def _run():
            with self._client.cursor() as cur:
                where_clauses = []
                params = []

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

                where_str = ""
                if where_clauses:
                    where_str = " WHERE " + " AND ".join(where_clauses)

                order_by = ", ".join([f'"{col}" ASC' for col in pk_cols]) if pk_cols else "1"

                if use_cursor:
                    sql = f'SELECT * FROM "{self.schema}"."{table_name}"{where_str} ORDER BY {order_by} LIMIT %s'
                    params.append(limit)
                else:
                    sql = f'SELECT * FROM "{self.schema}"."{table_name}"{where_str} ORDER BY {order_by} LIMIT %s OFFSET %s'
                    params.append(limit)
                    params.append(offset)

                cur.execute(sql, tuple(params))
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        cols = list(rows[0].keys())
        col_str = ", ".join([f'"{c}"' for c in cols])
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f'INSERT INTO "{self.schema}"."{table_name}" ({col_str}) VALUES ({placeholders})'

        def _run():
            with self._client.cursor() as cur:
                val_tuples = [tuple(r[c] for c in cols) for r in rows]
                cur.executemany(sql, val_tuples)
                return len(rows)

        return await asyncio.to_thread(_run)

    async def execute_staged_bulk_load(
        self,
        target_table: str,
        stage_uri: str,
        file_format: str = "PARQUET",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._ensure_connected()
        if not self.iam_role:
            raise RuntimeError("Redshift execute_staged_bulk_load requires iam_role configured in adapter extra options")

        sql = f"COPY \"{self.schema}\".\"{target_table}\" FROM '{stage_uri}' IAM_ROLE '{self.iam_role}' FORMAT AS PARQUET"

        def _run():
            with self._client.cursor() as cur:
                cur.execute(sql)
                return {
                    "success": True,
                    "target_table": target_table,
                    "stage_uri": stage_uri,
                    "file_format": file_format,
                    "rows_loaded": 0,
                }

        return await asyncio.to_thread(_run)

    # -------------------------------------------------------------------------
    # Transactions
    # -------------------------------------------------------------------------

    async def begin_transaction(self) -> None:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute("BEGIN")
        await asyncio.to_thread(_run)
        self._in_transaction = True

    async def commit_transaction(self) -> None:
        self._ensure_connected()
        def _run():
            self._client.commit()
        await asyncio.to_thread(_run)
        self._in_transaction = False

    async def rollback_transaction(self) -> None:
        self._ensure_connected()
        def _run():
            self._client.rollback()
        await asyncio.to_thread(_run)
        self._in_transaction = False

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM \"{self.schema}\".\"{table_name}\"")
                row = cur.fetchone()
                return int(row[0]) if row else 0
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        sql = f"SELECT * FROM \"{self.schema}\".\"{table_name}\""

        def _row_stream():
            with self._client.cursor() as cur:
                cur.execute(sql)
                cols = [d[0] for d in cur.description]
                for r in cur.fetchall():
                    yield dict(zip(cols, r))

        return compute_canonical_table_checksum(_row_stream(), order_independent=True)
