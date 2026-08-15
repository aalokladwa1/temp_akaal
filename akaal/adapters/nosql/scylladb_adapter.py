"""
Akaal — ScyllaDB Wide-Column Database Adapter
=============================================
100% Physical Reality Adapter for ScyllaDB reusing cassandra-driver CQL compatibility layer.
Preserves explicit SystemType.SCYLLADB identity and ScyllaDB-specific capability declarations.
Provides multi-column clustering tuple continuation (WHERE (ck1, ck2, ...) > (%s, %s, ...)),
fail-closed safety for mixed clustering orders, and token partition continuation.
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
                "SELECT column_name, type, kind, position, clustering_order FROM system_schema.columns WHERE keyspace_name = %s AND table_name = %s",
                (keyspace, table_name),
            )
            cols = []
            for r in rows:
                cols.append({
                    "column_name": r.column_name,
                    "data_type": str(r.type),
                    "kind": r.kind,
                    "position": getattr(r, "position", 0),
                    "clustering_order": getattr(r, "clustering_order", "none"),
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
                (keyspace,),
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
    # Data Operations (Multi-Column Clustering Tuple & Token Continuation)
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
                "SELECT column_name, kind, position, clustering_order FROM system_schema.columns WHERE keyspace_name = %s AND table_name = %s",
                (keyspace, table_name),
            )
            all_cols = list(cols_info)
            pk_rows = [r for r in all_cols if r.kind == "partition_key"]
            pk_rows.sort(key=lambda x: getattr(x, "position", 0))
            pk_cols = [r.column_name for r in pk_rows]

            ck_rows = [r for r in all_cols if r.kind == "clustering"]
            ck_rows.sort(key=lambda x: getattr(x, "position", 0))
            ck_cols = [r.column_name for r in ck_rows]

            orders = set(r.clustering_order.lower() for r in ck_rows if hasattr(r, "clustering_order") and r.clustering_order != "none")
            if len(orders) > 1:
                raise RuntimeError(f"Table '{table_name}' has mixed clustering column orders ({orders}). Mixed clustering order continuation is not supported; fail-closed for safety.")

            results = []

            # 1. Attempt multi-column clustering tuple continuation if clustering key values are present
            if last_processed_primary_key and pk_cols and ck_cols and all(k in last_processed_primary_key for k in pk_cols + ck_cols):
                pk_eq = " AND ".join([f'"{c}" = %s' for c in pk_cols])
                if len(ck_cols) == 1:
                    ck_name = ck_cols[0]
                    query_intra = f'SELECT * FROM "{keyspace}"."{table_name}" WHERE {pk_eq} AND "{ck_name}" > %s LIMIT {limit}'
                    vals_intra = tuple(last_processed_primary_key[c] for c in pk_cols) + (last_processed_primary_key[ck_name],)
                else:
                    ck_cols_str = ", ".join([f'"{c}"' for c in ck_cols])
                    ck_placeholders = ", ".join(["%s"] * len(ck_cols))
                    query_intra = f'SELECT * FROM "{keyspace}"."{table_name}" WHERE {pk_eq} AND ({ck_cols_str}) > ({ck_placeholders}) LIMIT {limit}'
                    vals_intra = tuple(last_processed_primary_key[c] for c in pk_cols) + tuple(last_processed_primary_key[c] for c in ck_cols)

                rows_intra = list(self._session.execute(query_intra, vals_intra))
                if rows_intra:
                    for r in rows_intra:
                        results.append(r._asdict())
                        if len(results) >= limit:
                            break
                    return results

            # 2. If no intra-partition rows found or no clustering keys, advance to next partition using token(...)
            if last_processed_primary_key and pk_cols and all(k in last_processed_primary_key for k in pk_cols):
                cols_str = ", ".join([f'"{c}"' for c in pk_cols])
                placeholders = ", ".join(["%s"] * len(pk_cols))
                vals = tuple(last_processed_primary_key[c] for c in pk_cols)
                query_next = f'SELECT * FROM "{keyspace}"."{table_name}" WHERE token({cols_str}) > token({placeholders}) LIMIT {limit}'
                rows_next = self._session.execute(query_next, vals)
                for r in rows_next:
                    results.append(r._asdict())
                    if len(results) >= limit:
                        break
                return results

            # 3. Initial fetch without checkpoint
            from cassandra.query import SimpleStatement
            stmt = SimpleStatement(f'SELECT * FROM "{keyspace}"."{table_name}"', fetch_size=limit)
            rows = self._session.execute(stmt)
            for r in rows:
                results.append(r._asdict())
                if len(results) >= limit:
                    break

            return results

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
