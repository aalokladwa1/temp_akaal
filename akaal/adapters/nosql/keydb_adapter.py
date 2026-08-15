"""
Akaal — KeyDB Multithreaded Key-Value Data Store Adapter
=========================================================
100% Physical Reality Adapter for KeyDB reusing redis-py wire protocol driver.
Preserves explicit SystemType.KEYDB identity and KeyDB-specific capability declarations.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.keydbadapter")


class KeyDBAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.KEYDB
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._client = None

    def _ensure_connected(self) -> None:
        if not self.is_connected or self._client is None:
            raise RuntimeError("KeyDB database connection is not active.")

    async def create_connection(self) -> Any:
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis is not installed. Run: pip install redis") from exc

        host = self.config.host or "localhost"
        port = self.config.port or 6379
        db = self.config.extra.get("db", 0) if self.config.extra else 0
        extra = self.config.extra or {}
        password = extra.get("password") or getattr(self.config, "password", None)

        def _connect():
            r = redis.Redis(host=host, port=port, db=db, password=password, socket_timeout=5)
            r.ping()
            return r

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        try:
            self._client = await self.create_connection()
            self.is_connected = True
            logger.info(f"[KeyDBAdapter] Connected physically to KeyDB database.")
        except Exception as exc:
            self.is_connected = False
            self._client = None
            raise RuntimeError(f"Failed to connect to physical KeyDB instance: {exc}") from exc

    async def close(self) -> None:
        if self._client:
            def _close():
                self._client.close()
            await asyncio.to_thread(_close)
            self._client = None
        self.is_connected = False
        logger.info("[KeyDBAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        def _run():
            return self._client.ping()
        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Schema Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        def _run():
            return ["keys", "string", "hash", "list", "set", "zset"]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return [
            {"column_name": "key", "data_type": "STRING", "nullable": False},
            {"column_name": "type", "data_type": "STRING", "nullable": False},
            {"column_name": "value", "data_type": "STRING", "nullable": True},
            {"column_name": "ttl", "data_type": "INTEGER", "nullable": True},
        ]

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

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
    # Data Operations
    # ------------------------------------------------------------------

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            cursor = 0
            keys = []
            while True:
                cursor, batch_keys = self._client.scan(cursor=cursor, count=limit)
                keys.extend(batch_keys)
                if cursor == 0 or len(keys) >= limit:
                    break
            keys = keys[:limit]
            pipe = self._client.pipeline()
            for k in keys:
                pipe.type(k)
                pipe.get(k)
                pipe.ttl(k)
            res = pipe.execute()
            rows = []
            for i in range(len(keys)):
                k = keys[i]
                k_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                k_type = res[i * 3]
                k_type_str = k_type.decode("utf-8") if isinstance(k_type, bytes) else str(k_type)
                val = res[i * 3 + 1]
                val_str = val.decode("utf-8") if isinstance(val, bytes) else str(val) if val is not None else None
                ttl = res[i * 3 + 2]
                rows.append({
                    "key": k_str,
                    "type": k_type_str,
                    "value": val_str,
                    "ttl": ttl,
                })
            return rows
        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        def _run():
            pipe = self._client.pipeline()
            for r in rows:
                k = r["key"]
                v = r.get("value", "")
                pipe.set(k, v)
                if "ttl" in r and r["ttl"] is not None and r["ttl"] > 0:
                    pipe.expire(k, r["ttl"])
            res = pipe.execute()
            return len(rows)
        return await asyncio.to_thread(_run)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        def _run():
            return self._client.dbsize()
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        def _row_stream():
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor=cursor, count=100)
                if not keys:
                    if cursor == 0:
                        break
                    continue
                pipe = self._client.pipeline()
                for k in keys:
                    pipe.get(k)
                vals = pipe.execute()
                for i in range(len(keys)):
                    k_str = keys[i].decode("utf-8") if isinstance(keys[i], bytes) else str(keys[i])
                    v_str = vals[i].decode("utf-8") if isinstance(vals[i], bytes) else str(vals[i]) if vals[i] else ""
                    yield {"key": k_str, "value": v_str}
                if cursor == 0:
                    break
        return compute_canonical_table_checksum(_row_stream(), order_independent=True)
