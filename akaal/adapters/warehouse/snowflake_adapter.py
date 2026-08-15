"""
Akaal — Snowflake Cloud Data Warehouse Adapter (P4.3 Physical Reality)
========================================================================
Physical BaseAdapter and IWarehouseCapability implementation for Snowflake.
Strict Zero-Fake Policy: Uses physical snowflake-connector-python driver.
Fails closed when disconnected or when driver is missing.
"""

import logging
import asyncio
import hashlib
from typing import Any, Dict, List, Optional

from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability
from akaal.connectors.contracts.warehouse import IWarehouseCapability

logger = logging.getLogger("akaal.adapters.snowflake")


class SnowflakeAdapter(BaseAdapter, IWarehouseCapability):
    """Physical Production Adapter for Snowflake Data Cloud."""

    SYSTEM_TYPE = SystemType.SNOWFLAKE
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
        self.account = extra.get("account") or getattr(config, "host", "")
        self.warehouse = extra.get("warehouse", "COMPUTE_WH")
        self.database = getattr(config, "database_name", "ANALYTICS_DB") or "ANALYTICS_DB"
        self.schema = extra.get("schema", "PUBLIC") or "PUBLIC"
        self.role = extra.get("role", "ACCOUNTADMIN")

    async def create_connection(self) -> Any:
        try:
            import snowflake.connector
        except Exception as exc:
            raise RuntimeError("snowflake-connector-python not installed. Run: pip install snowflake-connector-python") from exc

        if not self.account:
            raise RuntimeError("Adapter config must include Snowflake account identifier")

        extra = getattr(self.config, "extra", {}) or {}
        user = getattr(self.config, "username", None) or extra.get("username") or getattr(self.config, "credentials_ref", "")
        pwd = extra.get("password", "")

        def _connect():
            return snowflake.connector.connect(
                user=user,
                password=pwd,
                account=self.account,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
                role=self.role,
            )

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        """Establishes physical connection to Snowflake."""
        try:
            self._client = await self.create_connection()
            self.is_connected = True
            logger.info(f"[SnowflakeAdapter] Connected to Snowflake account {self.account}")
        except Exception as exc:
            self.is_connected = False
            self._client = None
            raise RuntimeError(f"Failed to connect to physical Snowflake database: {exc}") from exc

    async def close(self) -> None:
        """Closes physical Snowflake connection."""
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
        logger.info("[SnowflakeAdapter] Connection closed.")

    def _ensure_connected(self) -> None:
        if not self._client or not getattr(self, "is_connected", False):
            raise RuntimeError("Snowflake connection is not active.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        def _check():
            with self._client.cursor() as cur:
                cur.execute("SELECT CURRENT_VERSION()")
                row = cur.fetchone()
                return bool(row)
        return await asyncio.to_thread(_check)

    async def get_server_version(self) -> str:
        self._ensure_connected()
        def _get_ver():
            with self._client.cursor() as cur:
                cur.execute("SELECT CURRENT_VERSION()")
                row = cur.fetchone()
                return row[0] if row else "Snowflake"
        return await asyncio.to_thread(_get_ver)

    # -------------------------------------------------------------------------
    # Schema Discovery & Metadata
    # -------------------------------------------------------------------------

    async def discover_datasets(self) -> List[str]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SHOW SCHEMAS IN DATABASE \"{self.database}\"")
                return [f"{self.database}.{r[1]}" for r in cur.fetchall()]
        return await asyncio.to_thread(_run)

    async def discover_warehouse_tables(self, dataset_name: Optional[str] = None) -> List[str]:
        return await self.discover_tables()

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SELECT TABLE_NAME FROM \"{self.database}\".INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{self.schema}' AND TABLE_TYPE = 'BASE TABLE'")
                return [r[0] for r in cur.fetchall()]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM \"{self.database}\".INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{self.schema}' AND TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION")
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
                    cur.execute(f"SHOW PRIMARY KEYS IN TABLE \"{self.database}\".\"{self.schema}\".\"{table_name}\"")
                    return [r[4] for r in cur.fetchall()]
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
                cur.execute(f"SELECT TABLE_NAME, VIEW_DEFINITION FROM \"{self.database}\".INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = '{self.schema}'")
                return [{"view_name": r[0], "definition": r[1]} for r in cur.fetchall()]
        return await asyncio.to_thread(_run)

    async def get_clustering_metadata(self, table_name: str) -> Dict[str, Any]:
        self._ensure_connected()
        def _run():
            with self._client.cursor() as cur:
                cur.execute(f"SHOW TABLES LIKE '{table_name}' IN SCHEMA \"{self.database}\".\"{self.schema}\"")
                row = cur.fetchone()
                cluster_key = row[9] if row and len(row) > 9 else None
                return {
                    "table_name": table_name,
                    "clustering_key": cluster_key,
                    "automatic_clustering_enabled": bool(cluster_key),
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
                    sql = f'SELECT * FROM "{self.database}"."{self.schema}"."{table_name}"{where_str} ORDER BY {order_by} LIMIT %s'
                    params.append(limit)
                else:
                    sql = f'SELECT * FROM "{self.database}"."{self.schema}"."{table_name}"{where_str} ORDER BY {order_by} LIMIT %s OFFSET %s'
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
        sql = f'INSERT INTO "{self.database}"."{self.schema}"."{table_name}" ({col_str}) VALUES ({placeholders})'

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
        opts = options or {}
        on_error = opts.get("on_error", "ABORT_STATEMENT")
        sql = f"COPY INTO \"{self.database}\".\"{self.schema}\".\"{target_table}\" FROM '{stage_uri}' FILE_FORMAT = (TYPE = {file_format}) ON_ERROR = '{on_error}'"

        def _run():
            with self._client.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                loaded = sum([r[3] for r in rows if len(r) > 3 and isinstance(r[3], int)]) if rows else 0
                return {
                    "success": True,
                    "target_table": target_table,
                    "stage_uri": stage_uri,
                    "file_format": file_format,
                    "rows_loaded": loaded,
                }

        return await asyncio.to_thread(_run)

    async def unload_to_stage(
        self,
        source_table: str,
        stage_uri: str,
        file_format: str = "PARQUET",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._ensure_connected()
        sql = f"COPY INTO '{stage_uri}' FROM \"{self.database}\".\"{self.schema}\".\"{source_table}\" FILE_FORMAT = (TYPE = {file_format} COMPRESSION = SNAPPY) HEADER = TRUE"

        def _run():
            with self._client.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                unloaded = sum([r[2] for r in rows if len(r) > 2 and isinstance(r[2], int)]) if rows else 0
                return {
                    "success": True,
                    "source_table": source_table,
                    "stage_uri": stage_uri,
                    "rows_unloaded": unloaded,
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
                cur.execute(f"SELECT COUNT(*) FROM \"{self.database}\".\"{self.schema}\".\"{table_name}\"")
                row = cur.fetchone()
                return int(row[0]) if row else 0
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        sql = f"SELECT * FROM \"{self.database}\".\"{self.schema}\".\"{table_name}\""

        def _row_stream():
            with self._client.cursor() as cur:
                cur.execute(sql)
                cols = [d[0] for d in cur.description]
                for r in cur.fetchall():
                    yield dict(zip(cols, r))

        return compute_canonical_table_checksum(_row_stream(), order_independent=True)
