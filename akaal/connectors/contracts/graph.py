"""
AKAAL Graph, Key-Value & Search Engine Capability Extension Contracts (P4.1).
==============================================================================
Defines capability extension interfaces for:
- Graph databases (Neo4j, Amazon Neptune, Azure Cosmos DB Graph API)
- Key-Value stores (Redis, Memcached, DynamoDB Key-Value mode)
- Search engines (Elasticsearch, OpenSearch)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IGraphCapability(ABC):
    """Extension contract for graph databases (Neo4j, Neptune)."""

    @abstractmethod
    async def discover_node_labels(self) -> List[str]:
        """Discovers node labels."""
        pass

    @abstractmethod
    async def discover_relationship_types(self) -> List[str]:
        """Discovers relationship types."""
        pass

    @abstractmethod
    async def read_nodes_batch(self, label: str, skip: int, limit: int) -> List[Dict[str, Any]]:
        """Reads batch of graph nodes."""
        pass

    @abstractmethod
    async def read_relationships_batch(self, rel_type: str, skip: int, limit: int) -> List[Dict[str, Any]]:
        """Reads batch of graph relationships."""
        pass


class IKeyValueCapability(ABC):
    """Extension contract for key-value stores (Redis, DynamoDB KV)."""

    @abstractmethod
    async def discover_key_namespaces(self) -> List[str]:
        """Discovers key prefixes or databases."""
        pass

    @abstractmethod
    async def scan_keys_batch(self, cursor: int, pattern: str = "*", count: int = 100) -> Dict[str, Any]:
        """Scans keys using cursor semantics."""
        pass

    @abstractmethod
    async def get_key_value(self, key: str) -> Optional[Any]:
        """Retrieves value for key."""
        pass

    @abstractmethod
    async def set_key_value(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Sets value for key."""
        pass


class ISearchCapability(ABC):
    """Extension contract for search engines (Elasticsearch, OpenSearch)."""

    @abstractmethod
    async def discover_indexes(self) -> List[str]:
        """Discovers search index names."""
        pass

    @abstractmethod
    async def get_index_mapping(self, index_name: str) -> Dict[str, Any]:
        """Retrieves index field mappings."""
        pass

    @abstractmethod
    async def scroll_documents(self, index_name: str, scroll_id: Optional[str] = None, batch_size: int = 100) -> Dict[str, Any]:
        """Scrolls documents across search index."""
        pass

    @abstractmethod
    async def bulk_index_documents(self, index_name: str, documents: List[Dict[str, Any]]) -> int:
        """Bulk indexes documents into target search index."""
        pass
