"""
AKAAL Wide-Column Database Capability Extension Contract (P4.1).
=================================================================
Defines wide-column database capability extension interfaces:
- Apache Cassandra, ScyllaDB, Google Cloud Bigtable, HBase
- Keyspaces, column families/tables, partition keys, clustering columns
- Consistency level declaration and token range partitioned reads
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IWideColumnCapability(ABC):
    """Extension contract for wide-column NoSQL databases (Cassandra, ScyllaDB, HBase)."""

    @abstractmethod
    async def discover_keyspaces(self) -> List[str]:
        """Discovers keyspace names."""
        pass

    @abstractmethod
    async def discover_column_families(self, keyspace: Optional[str] = None) -> List[str]:
        """Discovers tables/column families in keyspace."""
        pass

    @abstractmethod
    async def get_partition_key_metadata(self, table_name: str, keyspace: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves partition key and clustering column metadata."""
        pass

    @abstractmethod
    async def read_token_range_batch(
        self,
        table_name: str,
        start_token: int,
        end_token: int,
        limit: int = 1000,
        keyspace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Reads rows within token partition range."""
        pass
