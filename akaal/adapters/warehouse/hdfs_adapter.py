"""
Akaal — HDFS (Hadoop) Adapter
=============================
Implements BaseAdapter for HDFS (Hadoop).

Dependencies:
    hdfs

Install:
    pip install hdfs

Status: STUB — implement connect(), read_batch(), write_batch() with real SDK calls.
"""

import logging
from typing import Any, Dict, List
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.hdfsadapter")


class HDFSAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.HDFS
    CAPABILITIES = [AdapterCapability.BULK_READ, AdapterCapability.BULK_WRITE, AdapterCapability.STREAMING_READ, AdapterCapability.OBJECT_STORAGE]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._client = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        TODO: Implement using hdfs
        Example:
            import hdfs
            self._client = hdfs.connect(...)
        """
        raise NotImplementedError("HDFSAdapter.connect() not yet implemented. Install: hdfs")

    async def close(self) -> None:
        if self._client:
            # TODO: self._client.close()
            self._client = None
        self.is_connected = False
        logger.info("[HDFSAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        raise NotImplementedError("HDFSAdapter.check_permissions() not yet implemented.")

    # ------------------------------------------------------------------
    # Schema Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        raise NotImplementedError("HDFSAdapter.discover_tables() not yet implemented.")

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("HDFSAdapter.discover_columns() not yet implemented.")

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("HDFSAdapter.discover_foreign_keys() not yet implemented.")

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("HDFSAdapter.discover_indexes() not yet implemented.")

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("HDFSAdapter.discover_constraints() not yet implemented.")

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("HDFSAdapter.discover_triggers() not yet implemented.")

    async def discover_views(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("HDFSAdapter.discover_views() not yet implemented.")

    # ------------------------------------------------------------------
    # Data Operations
    # ------------------------------------------------------------------

    async def read_batch(self, table_name: str, offset: int, limit: int) -> List[Dict[str, Any]]:
        raise NotImplementedError("HDFSAdapter.read_batch() not yet implemented.")

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        raise NotImplementedError("HDFSAdapter.write_batch() not yet implemented.")

    async def get_row_count(self, table_name: str) -> int:
        raise NotImplementedError("HDFSAdapter.get_row_count() not yet implemented.")

    async def compute_checksum(self, table_name: str) -> str:
        raise NotImplementedError("HDFSAdapter.compute_checksum() not yet implemented.")
