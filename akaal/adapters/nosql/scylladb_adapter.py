"""
Akaal — ScyllaDB Wide-Column Database Adapter
=============================================
100% Physical Reality Adapter for ScyllaDB reusing cassandra-driver CQL compatibility layer.
Preserves explicit SystemType.SCYLLADB identity and ScyllaDB-specific capability declarations.
Provides token/keyset continuation pagination preventing first-page repetition.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.scylladbadapter")


class ScyllaDBAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.SCYLLADB
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._cluster = None
        self._session = None

    def _ensure_connected(self) -> None:
        if not self.is_connected or self._session is None:
            raise RuntimeError("ScyllaDB database connection is not active.")

    async def create_connection(self) -> Any:
        try:
            from cassandra.cluster import Cluster
        except ImportError as exc:
            raise RuntimeError("cassandra-driver is not installed. Run: pip install cassandra-driver") from exc

        host = self.config.host or "127.0.0.1"
        port = self.config.port or 9042
        keyspace = self.config.database_name or "system"

        def _connect():
            cluster = Cluster([host], port=port)
            session = cluster.connect(keyspace)
            return cluster, session

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        try:
            self._cluster, self._session = await self.create_connection()
            self.is_connected = True
            logger.info(f"[ScyllaDBAdapter] Connected physically to ScyllaDB cluster keyspace '{self.config.database_name}'.")
        except Exception as exc:
            self.is_connected = False
            self._cluster = None
            self._session = None
            raise RuntimeError(f"Failed to connect to physical ScyllaDB cluster: {exc}") from exc

    async def close(self) -> None:
        if self._cluster:
            def _close():
                self._cluster.shutdown()
            await asyncio.to_thread(_close)
            self._cluster = None
            self._session = None
        self.is_connected = False
        logger.info("[ScyllaDBAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        def _run():
            rows = self._session.execute("SELECT release_version FROM system.local")
            return bool(rows)
        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Schema Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        keyspace = self.config.database_name or "system"
        def _run():
            rows = self._session.execute(
                "SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s",
                (keyspace,),
            )
            return [r.table_name for r in rows]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        keyspace = self.config.database_name or "system"
        def _run():
            rows = self._session.execute(
                "SELECT column_name, type, kind FROM system_schema.columns WHERE keyspace_name = %s AND table_name = %s",
                (keyspace, table_name),
            )
            cols = []
            for r in rows:
                cols.append({
                    "column_name": r.column_name,
                    "data_type": str(r.type),
                    "kind": r.kind,
                    "nullable": r.kind not in ("partition_key", "clustering"),
                })
            return cols
        return await asyncio.to_thread(_run)

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        keyspace = self.config.database_name or "system"
        def _run():
            rows = self._session.execute(
                "SELECT index_name FROM system_schema.indexes WHERE keyspace_name = %s AND table_name = %s",
                (keyspace, table_name),
            )
            return [{"index_name": r.index_name} for r in rows]
        return await asyncio.to_thread(_run)

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def discover_views(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    # ------------------------------------------------------------------
    # Data Operations (Token Continuation & Paging)
    # ------------------------------------------------------------------

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        keyspace = self.config.database_name or "system"
        def _run():
            cols_info = self._session.execute(
                "SELECT column_name, kind FROM system_schema.columns WHERE keyspace_name = %s AND table_name = %s",
                (keyspace, table_name),
            )
            pk_cols = [r.column_name for r in cols_info if r.kind == "partition_key"]

            if last_processed_primary_key and pk_cols and all(k in last_processed_primary_key for k in pk_cols):
                pk_name = pk_cols[0]
                val = last_processed_primary_key[pk_name]
                query = f'SELECT * FROM "{keyspace}"."{table_name}" WHERE token("{pk_name}") > token(%s) LIMIT {limit}'
                rows = self._session.execute(query, (val,))
            else:
                from cassandra.query import SimpleStatement
                stmt = SimpleStatement(f'SELECT * FROM "{keyspace}"."{table_name}"', fetch_size=limit)
                rows = self._session.execute(stmt)

            result = []
            for r in rows:
                result.append(r._asdict())
                if len(result) >= limit:
                    break
            return result

        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        keyspace = self.config.database_name or "system"
        cols = list(rows[0].keys())
        col_str = ", ".join([f'"{c}"' for c in cols])
        placeholders = ", ".join(["%s"] * len(cols))
        query = f'INSERT INTO "{keyspace}"."{table_name}" ({col_str}) VALUES ({placeholders})'

        def _run():
            count = 0
            for r in rows:
                vals = tuple(r[c] for c in cols)
                self._session.execute(query, vals)
                count += 1
            return count
        return await asyncio.to_thread(_run)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        keyspace = self.config.database_name or "system"
        def _run():
            rows = self._session.execute(f'SELECT COUNT(*) FROM "{keyspace}"."{table_name}"')
            r = rows.one()
            return int(r[0]) if r else 0
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        keyspace = self.config.database_name or "system"
        def _row_stream():
            rows = self._session.execute(f'SELECT * FROM "{keyspace}"."{table_name}"')
            for r in rows:
                yield r._asdict()
        return compute_canonical_table_checksum(_row_stream(), order_independent=True)
