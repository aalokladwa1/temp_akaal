"""
Akaal — Microsoft SQL Server Adapter
====================================
Implements BaseAdapter for Microsoft SQL Server.

Dependencies:
    aioodbc

Install:
    pip install aioodbc

Status: STUB — implement connect(), read_batch(), write_batch() with real SDK calls.
"""

import logging
from typing import Any, Dict, List
from akaal.adapters.base_adapter import BaseAdapter
from akaal.core.models.enums import SystemType, AdapterCapability

logger = logging.getLogger("akaal.adapters.mssqladapter")


class MSSQLAdapter(BaseAdapter):

    SYSTEM_TYPE = SystemType.MSSQL
    CAPABILITIES = [AdapterCapability.SCHEMA_DISCOVERY, AdapterCapability.BULK_READ, AdapterCapability.BULK_WRITE, AdapterCapability.CDC_SUPPORT, AdapterCapability.TRANSACTION_SUPPORT]

    def __init__(self, config) -> None:
        super().__init__(config)
        self._client = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        TODO: Implement using aioodbc
        Example:
            import aioodbc
            self._client = aioodbc.connect(...)
        """
        raise NotImplementedError("MSSQLAdapter.connect() not yet implemented. Install: aioodbc")

    async def close(self) -> None:
        if self._client:
            # TODO: self._client.close()
            self._client = None
        self.is_connected = False
        logger.info("[MSSQLAdapter] Connection closed.")

    async def check_permissions(self) -> bool:
        raise NotImplementedError("MSSQLAdapter.check_permissions() not yet implemented.")

    # ------------------------------------------------------------------
    # Schema Discovery
    # ------------------------------------------------------------------

    async def discover_tables(self) -> List[str]:
        raise NotImplementedError("MSSQLAdapter.discover_tables() not yet implemented.")

    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("MSSQLAdapter.discover_columns() not yet implemented.")

    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("MSSQLAdapter.discover_foreign_keys() not yet implemented.")

    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("MSSQLAdapter.discover_indexes() not yet implemented.")

    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("MSSQLAdapter.discover_constraints() not yet implemented.")

    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("MSSQLAdapter.discover_triggers() not yet implemented.")

    async def discover_views(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("MSSQLAdapter.discover_views() not yet implemented.")

    # ------------------------------------------------------------------
    # Data Operations
    # ------------------------------------------------------------------

    async def read_batch(self, table_name: str, offset: int, limit: int) -> List[Dict[str, Any]]:
        raise NotImplementedError("MSSQLAdapter.read_batch() not yet implemented.")

    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        raise NotImplementedError("MSSQLAdapter.write_batch() not yet implemented.")

    async def get_row_count(self, table_name: str) -> int:
        raise NotImplementedError("MSSQLAdapter.get_row_count() not yet implemented.")

    async def compute_checksum(self, table_name: str) -> str:
        raise NotImplementedError("MSSQLAdapter.compute_checksum() not yet implemented.")
