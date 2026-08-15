"""
Akaal — MongoDB Document Database Adapter
=========================================
100% Physical Reality Adapter for MongoDB using pymongo.
Provides fail-closed connectivity, database/collection discovery, document batch reads,
bulk write ingestion, BSON type handling, and streaming canonical checksum validation.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.mongodbadapter")


class MongoDBAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.MONGODB
    CAPABILITIES = [
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._client = None
        self._db = None

    def _ensure_connected(self) -> None:
        if not self.is_connected or self._client is None:
            raise RuntimeError("MongoDB database connection is not active.")

    async def create_connection(self) -> Any:
        try:
            import pymongo
        except ImportError as exc:
            raise RuntimeError("pymongo is not installed. Run: pip install pymongo") from exc

        host = self.config.host or "localhost"
        port = self.config.port or 27017
        database_name = self.config.database_name or "admin"
        extra = self.config.extra or {}
        username = extra.get("username") or getattr(self.config, "username", None)
        password = extra.get("password") or getattr(self.config, "password", None)

        def _connect():
            if username and password:
                client = pymongo.MongoClient(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    serverSelectionTimeoutMS=5000,
                )
            else:
                client = pymongo.MongoClient(
                    host=host,
                    port=port,
                    serverSelectionTimeoutMS=5000,
                )
            # Validate physical ping
            client.admin.command("ping")
            return client

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        try:
            self._client = await self.create_connection()
            db_name = self.config.database_name or "test"
            self._db = self._client[db_name]
            self.is_connected = True
            logger.info(f"[MongoDBAdapter] Connected physically to MongoDB database '{db_name}'.")
        except Exception as exc:
            self.is_connected = False
            self._client = None
            self._db = None
            raise RuntimeError(f"Failed to connect to physical MongoDB database: {exc}") from exc

    async def close(self) -> None:
        if self._client:
            def _close():
                self._client.close()
            await asyncio.to_thread(_close)
            self._client = None
            self._db = None
        self.is_connected = False
        logger.info("[MongoDBAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        def _run():
            res = self._db.command("connectionStatus")
            return res.get("ok") == 1.0
        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Schema / Collection Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        def _run():
            return self._db.list_collection_names()
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            coll = self._db[table_name]
            sample = coll.find_one()
            if not sample:
                return [{"column_name": "_id", "data_type": "ObjectId", "nullable": False}]
            cols = []
            for k, v in sample.items():
                cols.append({
                    "column_name": k,
                    "data_type": type(v).__name__,
                    "nullable": True if k != "_id" else False,
                })
            return cols
        return await asyncio.to_thread(_run)

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return []

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        def _run():
            idx_info = self._db[table_name].index_information()
            res = []
            for name, spec in idx_info.items():
                res.append({
                    "index_name": name,
                    "keys": spec.get("key", []),
                    "unique": spec.get("unique", False),
                })
            return res
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
            cursor = self._db[table_name].find().skip(offset).limit(limit)
            rows = []
            for doc in cursor:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                rows.append(doc)
            return rows
        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        def _run():
            res = self._db[table_name].insert_many(rows)
            return len(res.inserted_ids)
        return await asyncio.to_thread(_run)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        def _run():
            return self._db[table_name].count_documents({})
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        def _row_stream():
            cursor = self._db[table_name].find()
            for doc in cursor:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                yield doc
        return compute_canonical_table_checksum(_row_stream(), order_independent=True)
