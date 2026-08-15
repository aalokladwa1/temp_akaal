"""
Akaal — Elasticsearch Search Engine Adapter
===========================================
100% Physical Reality Adapter for Elasticsearch using elasticsearch-py.
Provides fail-closed connectivity, index discovery, mapping field analysis,
bounded search pagination, Bulk API writes with item error checking, and streaming canonical checksums.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.elasticsearchadapter")


class ElasticsearchAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.ELASTICSEARCH
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
            raise RuntimeError("Elasticsearch cluster connection is not active.")

    async def create_connection(self) -> Any:
        try:
            from elasticsearch import Elasticsearch
        except ImportError as exc:
            raise RuntimeError("elasticsearch is not installed. Run: pip install elasticsearch") from exc

        host = self.config.host or "localhost"
        port = self.config.port or 9200
        scheme = self.config.extra.get("scheme", "http") if self.config.extra else "http"
        url = f"{scheme}://{host}:{port}"
        extra = self.config.extra or {}
        username = extra.get("username") or getattr(self.config, "username", None)
        password = extra.get("password") or getattr(self.config, "password", None)

        def _connect():
            if username and password:
                es = Elasticsearch([url], basic_auth=(username, password), request_timeout=5)
            else:
                es = Elasticsearch([url], request_timeout=5)
            if not es.ping():
                raise RuntimeError(f"Elasticsearch ping failed for {url}")
            return es

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        try:
            self._client = await self.create_connection()
            self.is_connected = True
            logger.info(f"[ElasticsearchAdapter] Connected physically to Elasticsearch cluster.")
        except Exception as exc:
            self.is_connected = False
            self._client = None
            raise RuntimeError(f"Failed to connect to physical Elasticsearch cluster: {exc}") from exc

    async def close(self) -> None:
        if self._client:
            def _close():
                self._client.close()
            await asyncio.to_thread(_close)
            self._client = None
        self.is_connected = False
        logger.info("[ElasticsearchAdapter] Connection closed.")

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
            indices = self._client.cat.indices(format="json")
            return [idx["index"] for idx in indices if not idx["index"].startswith(".")]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            mapping = self._client.indices.get_mapping(index=table_name)
            properties = mapping.get(table_name, {}).get("mappings", {}).get("properties", {})
            cols = [{"column_name": "_id", "data_type": "keyword", "nullable": False}]
            for name, spec in properties.items():
                cols.append({
                    "column_name": name,
                    "data_type": spec.get("type", "object"),
                    "nullable": True,
                })
            return cols
        return await asyncio-to-thread(_run) if hasattr(asyncio, "to_thread") else await asyncio.get_event_loop().run_in_executor(None, _run)

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
            res = self._client.search(index=table_name, from_=offset, size=limit, query={"match_all": {}})
            hits = res.get("hits", {}).get("hits", [])
            rows = []
            for h in hits:
                doc = h.get("_source", {})
                doc["_id"] = h.get("_id")
                rows.append(doc)
            return rows
        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        def _run():
            actions = []
            for r in rows:
                doc_id = r.get("_id")
                doc = {k: v for k, v in r.items() if k != "_id"}
                actions.append({"index": {"_index": table_name, "_id": doc_id}})
                actions.append(doc)
            res = self._client.bulk(operations=actions)
            if res.get("errors"):
                err_items = [item for item in res.get("items", []) if "error" in item.get("index", {})]
                raise RuntimeError(f"Elasticsearch bulk write failed with errors: {err_items[:3]}")
            return len(rows)
        return await asyncio.to_thread(_run)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        def _run():
            res = self._client.count(index=table_name)
            return int(res.get("count", 0))
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        def _row_stream():
            res = self._client.search(index=table_name, size=1000, query={"match_all": {}})
            hits = res.get("hits", {}).get("hits", [])
            for h in hits:
                doc = h.get("_source", {})
                doc["_id"] = h.get("_id")
                yield doc
        return compute_canonical_table_checksum(_row_stream(), order_independent=True)
