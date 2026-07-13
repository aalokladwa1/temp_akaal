"""
Akaal — IBM Db2 Adapter
=======================
Implements BaseAdapter for IBM Db2.

Dependencies:
    ibm_db

Install:
    pip install ibm_db

Status: STUB — implement connect(), read_batch(), write_batch() with real SDK calls.
"""

import logging
from typing import Any, Dict, List, Optional
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.ibmdb2adapter")


class IBMDB2Adapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.IBM_DB2
    CAPABILITIES = [AdapterCapability.SCHEMA_DISCOVERY, AdapterCapability.BULK_READ, AdapterCapability.BULK_WRITE, AdapterCapability.TRANSACTION_SUPPORT]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._client = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        TODO: Implement using ibm_db
        Example:
            import ibm_db
            self._client = ibm_db.connect(...)
        """
        raise NotImplementedError("IBMDB2Adapter.connect() not yet implemented. Install: ibm_db")

    async def close(self) -> None:
        if self._client:
            # TODO: self._client.close()
            self._client = None
        self.is_connected = False
        logger.info("[IBMDB2Adapter] Connection closed.")

    async def check_permissions(self) -> bool:
        raise NotImplementedError("IBMDB2Adapter.check_permissions() not yet implemented.")

    # ------------------------------------------------------------------
    # Schema Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        raise NotImplementedError("IBMDB2Adapter.discover_tables() not yet implemented.")

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("IBMDB2Adapter.discover_columns() not yet implemented.")

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("IBMDB2Adapter.discover_foreign_keys() not yet implemented.")

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("IBMDB2Adapter.discover_indexes() not yet implemented.")

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("IBMDB2Adapter.discover_constraints() not yet implemented.")

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("IBMDB2Adapter.discover_triggers() not yet implemented.")

    async def discover_views(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("IBMDB2Adapter.discover_views() not yet implemented.")

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
        raise NotImplementedError("IBMDB2Adapter.read_batch() not yet implemented.")

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        raise NotImplementedError("IBMDB2Adapter.write_batch() not yet implemented.")

    async def get_row_count(self, table_name: str) -> int:
        raise NotImplementedError("IBMDB2Adapter.get_row_count() not yet implemented.")

    async def compute_checksum(self, table_name: str) -> str:
        raise NotImplementedError("IBMDB2Adapter.compute_checksum() not yet implemented.")
