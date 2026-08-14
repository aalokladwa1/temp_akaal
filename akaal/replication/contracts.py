"""
AKAAL Replication Engine — Canonical Universal Physical Transport Contracts
=============================================================================
Defines system-agnostic IPhysicalReader and IPhysicalWriter contracts and DTOs
used by all database connectors (Oracle, PostgreSQL, MySQL, MSSQL, etc.).
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional

from akaal.engine.spec import TransportPartition, BatchMetadata

logger = logging.getLogger("akaal.replication.contracts")


class ConnectorCapability:
    """Capability declaration flags for database readers and writers."""

    def __init__(
        self,
        can_read: bool = True,
        can_write: bool = True,
        supports_transactions: bool = True,
        supports_upsert: bool = True,
        supports_range_partitioning: bool = True,
        supports_lob_streaming: bool = True,
        supports_connection_pooling: bool = True,
    ):
        self.can_read = can_read
        self.can_write = can_write
        self.supports_transactions = supports_transactions
        self.supports_upsert = supports_upsert
        self.supports_range_partitioning = supports_range_partitioning
        self.supports_lob_streaming = supports_lob_streaming
        self.supports_connection_pooling = supports_connection_pooling

    def to_dict(self) -> Dict[str, bool]:
        return {
            "can_read": self.can_read,
            "can_write": self.can_write,
            "supports_transactions": self.supports_transactions,
            "supports_upsert": self.supports_upsert,
            "supports_range_partitioning": self.supports_range_partitioning,
            "supports_lob_streaming": self.supports_lob_streaming,
            "supports_connection_pooling": self.supports_connection_pooling,
        }


class IPhysicalReader(ABC):
    """Canonical interface for partition-bounded database physical readers."""

    @abstractmethod
    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        """Open database connection and prepare streaming query cursor for a given partition."""
        pass

    @abstractmethod
    def read_batch(self, batch_size: int) -> Tuple[List[Tuple], BatchMetadata]:
        """Fetch next bounded batch of normalized tuples and batch metadata."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release cursor and database connection back to pool."""
        pass

    def get_capabilities(self) -> ConnectorCapability:
        """Return reader capability declaration."""
        return ConnectorCapability(can_read=True, can_write=False)


class IPhysicalWriter(ABC):
    """Canonical interface for high-performance database physical writers."""

    @abstractmethod
    def write_batch(
        self,
        table_name: str,
        columns: List[str],
        data: List[Tuple],
        batch_meta: BatchMetadata,
        pk_columns: Optional[List[str]] = None,
        target_schema: str = "public",
        page_size: int = 5000,
        allow_merge: bool = True,
    ) -> int:
        """Execute parameterized batch write/upsert into target table and return rows written count."""
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit active batch transaction."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Roll back active batch transaction on error."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release cursor and database connection back to pool."""
        pass

    def get_capabilities(self) -> ConnectorCapability:
        """Return writer capability declaration."""
        return ConnectorCapability(can_read=False, can_write=True)
