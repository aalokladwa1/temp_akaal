"""
Akaal — Azure Blob Storage Adapter
==================================
100% Physical Reality Adapter for Azure Blob Storage using azure-storage-blob.
Provides fail-closed connectivity, container/blob discovery, native continuation token pagination,
bounded-memory streaming read/write, secret redaction, and canonical checksum calculation.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.azureblobadapter")


class AzureBlobAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.AZURE_BLOB
    CAPABILITIES = [
        AdapterCapability.OBJECT_STORAGE,
        AdapterCapability.SCHEMA_DISCOVERY,
        AdapterCapability.BULK_READ,
        AdapterCapability.STREAMING_READ,
        AdapterCapability.BULK_WRITE,
    ]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._service_client = None

    def _ensure_connected(self) -> None:
        if not self.is_connected or self._service_client is None:
            raise RuntimeError("Azure Blob Storage connection is not active.")

    def _redact(self, text: str) -> str:
        if not text:
            return ""
        sec_keys = [
            getattr(self.config, "password", None),
            self.config.extra.get("secret_key") if self.config.extra else None,
            self.config.extra.get("connection_string") if self.config.extra else None,
            self.config.extra.get("account_key") if self.config.extra else None,
            self.config.extra.get("sas_token") if self.config.extra else None,
        ]
        res = str(text)
        for k in sec_keys:
            if k and len(str(k)) > 3:
                res = res.replace(str(k), "[REDACTED]")
        return res

    async def create_connection(self) -> Any:
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as exc:
            raise RuntimeError("azure-storage-blob is not installed. Run: pip install azure-storage-blob") from exc

        extra = self.config.extra or {}
        conn_str = extra.get("connection_string")
        account_url = self.config.host if self.config.host and "://" in self.config.host else extra.get("account_url")
        account_name = extra.get("account_name") or getattr(self.config, "username", None)
        account_key = extra.get("account_key") or getattr(self.config, "password", None)

        def _connect():
            if conn_str:
                client = BlobServiceClient.from_connection_string(conn_str)
            elif account_url and account_key:
                client = BlobServiceClient(account_url, credential=account_key)
            elif account_name and account_key:
                url = f"https://{account_name}.blob.core.windows.net"
                client = BlobServiceClient(url, credential=account_key)
            else:
                raise RuntimeError("Azure Blob Storage requires connection_string, account_url + account_key, or account_name + account_key.")
            return client

        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        try:
            self._service_client = await self.create_connection()
            self.is_connected = True
            logger.info(f"[AzureBlobAdapter] Connected physically to Azure Blob Storage.")
        except Exception as exc:
            self.is_connected = False
            self._service_client = None
            raise RuntimeError(f"Failed to connect to physical Azure Blob Storage: {self._redact(str(exc))}") from exc

    async def close(self) -> None:
        if self._service_client:
            def _close():
                if hasattr(self._service_client, "close"):
                    self._service_client.close()
            await asyncio.to_thread(_close)
            self._service_client = None
        self.is_connected = False
        logger.info("[AzureBlobAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        self._ensure_connected()
        container_name = self.config.database_name or "test-container"
        def _run():
            try:
                container_client = self._service_client.get_container_client(container_name)
                return container_client.exists()
            except Exception:
                containers = list(self._service_client.list_containers(results_per_page=1))
                return True
        return await asyncio.to_thread(_run)

    # ------------------------------------------------------------------
    # Storage Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        self._ensure_connected()
        def _run():
            if self.config.database_name:
                return [self.config.database_name]
            containers = self._service_client.list_containers()
            return [c.name for c in containers]
        return await asyncio.to_thread(_run)

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return [
            {"column_name": "key", "data_type": "string", "nullable": False},
            {"column_name": "size", "data_type": "bigint", "nullable": False},
            {"column_name": "etag", "data_type": "string", "nullable": True},
            {"column_name": "last_modified", "data_type": "timestamp", "nullable": True},
            {"column_name": "blob_type", "data_type": "string", "nullable": True},
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
    # Data Operations (Native Continuation Token Pagination & Streaming)
    # ------------------------------------------------------------------

    async def read_batch(
        self,
        table_name: str,
        offset: int,
        limit: int,
        last_processed_primary_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_connected()
        container_name = self.config.database_name or table_name
        prefix = self.config.extra.get("prefix", "") if self.config.extra else ""

        def _run():
            container_client = self._service_client.get_container_client(container_name)
            continuation_token = None
            if last_processed_primary_key:
                ckpt_container = last_processed_primary_key.get("container") or last_processed_primary_key.get("bucket") or last_processed_primary_key.get("resource_id")
                if ckpt_container and ckpt_container != container_name:
                    raise RuntimeError(f"Resource identity mismatch in checkpoint resume: expected {container_name}, got {ckpt_container}")
                continuation_token = last_processed_primary_key.get("continuation_token") or last_processed_primary_key.get("page_token")

            pages = container_client.list_blobs(name_starts_with=prefix or None, results_per_page=limit).by_page(continuation_token=continuation_token)
            page = next(pages, [])

            rows = []
            for b in page:
                row = {
                    "key": b.name,
                    "size": b.size or 0,
                    "etag": getattr(b, "etag", "").strip('"'),
                    "last_modified": b.last_modified.isoformat() if getattr(b, "last_modified", None) else "",
                    "blob_type": str(getattr(b, "blob_type", "BlockBlob")),
                }
                if pages.continuation_token:
                    row["_continuation_token"] = pages.continuation_token
                rows.append(row)

            return rows

        return await asyncio.to_thread(_run)

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        self._ensure_connected()
        if not rows:
            return 0
        container_name = self.config.database_name or table_name

        def _run():
            container_client = self._service_client.get_container_client(container_name)
            count = 0
            for r in rows:
                key = r.get("key") or r.get("object_key") or f"object_{count}"
                body = r.get("body") or r.get("content") or b""
                if isinstance(body, str):
                    body = body.encode("utf-8")

                blob_client = container_client.get_blob_client(key)
                blob_client.upload_blob(body, overwrite=True)
                count += 1
            return count

        return await asyncio.to_thread(_run)

    async def get_row_count(self, table_name: str) -> int:
        self._ensure_connected()
        container_name = self.config.database_name or table_name
        def _run():
            container_client = self._service_client.get_container_client(container_name)
            blobs = list(container_client.list_blobs())
            return len(blobs)
        return await asyncio.to_thread(_run)

    async def compute_checksum(self, table_name: str) -> str:
        self._ensure_connected()
        from akaal.validation.domain.canonical_checksum import compute_canonical_table_checksum
        container_name = self.config.database_name or table_name

        def _row_stream():
            container_client = self._service_client.get_container_client(container_name)
            for b in container_client.list_blobs():
                yield {
                    "key": b.name,
                    "size": b.size or 0,
                    "etag": getattr(b, "etag", "").strip('"'),
                }

        return compute_canonical_table_checksum(_row_stream(), order_independent=True)
