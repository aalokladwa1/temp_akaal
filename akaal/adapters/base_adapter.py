"""
Akaal — Base Adapter
=====================
Abstract interface every database/storage adapter must implement.
All 17 supported systems plug into this contract.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from akaal.core.models.enums import AdapterCapability, SystemType


class BaseAdapter(ABC):
    """
    Abstract base for all Akaal database adapters.

    Every source and target adapter must implement this interface.
    Adapters are the ONLY place where database-specific logic lives.
    Core migration agents remain DB-agnostic.
    """

    SYSTEM_TYPE: SystemType = None          # Set by each subclass
    CAPABILITIES: List[AdapterCapability] = []  # Declared by each subclass

    def __init__(self, config: "ConnectionConfig") -> None:
        self.config = config
        self.is_connected = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the source/target system."""

    @abstractmethod
    async def close(self) -> None:
        """Close the connection cleanly."""

    @abstractmethod
    async def check_permissions(self) -> bool:
        """
        Verify credentials have appropriate permissions.
        Source adapters MUST confirm read-only access.
        """

    # ------------------------------------------------------------------
    # Schema discovery (RDBMS / structured)
    # ------------------------------------------------------------------

    @abstractmethod
    async def discover_tables(self) -> List[str]:
        """Return all table/collection/index names."""

    @abstractmethod
    async def discover_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Return column/field metadata for a table/collection."""

    @abstractmethod
    async def discover_foreign_keys(self) -> List[Dict[str, Any]]:
        """Return all relationships/references across the schema."""

    @abstractmethod
    async def discover_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Return index metadata."""

    @abstractmethod
    async def discover_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        """Return constraint metadata."""

    @abstractmethod
    async def discover_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        """Return trigger definitions."""

    @abstractmethod
    async def discover_views(self) -> List[Dict[str, Any]]:
        """Return view definitions."""

    # ------------------------------------------------------------------
    # Data operations
    # ------------------------------------------------------------------

    @abstractmethod
    async def read_batch(self, table_name: str, offset: int, limit: int) -> List[Dict[str, Any]]:
        """Read a batch of rows/documents from source."""

    @abstractmethod
    async def write_batch(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        """Write a batch of rows/documents to target. Returns rows written."""

    @abstractmethod
    async def get_row_count(self, table_name: str) -> int:
        """Return total row/document count for a table/collection."""

    @abstractmethod
    async def compute_checksum(self, table_name: str) -> str:
        """Compute a deterministic checksum of table contents."""

    # ------------------------------------------------------------------
    # CDC support (optional — override if supported)
    # ------------------------------------------------------------------

    def supports_cdc(self) -> bool:
        return AdapterCapability.CDC_SUPPORT in self.CAPABILITIES

    async def start_cdc_stream(self, table_names: List[str]) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} does not support CDC.")

    async def stop_cdc_stream(self) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} does not support CDC.")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"type={self.SYSTEM_TYPE}, "
            f"host={getattr(self.config, 'host', '?')}, "
            f"connected={self.is_connected})"
        )
