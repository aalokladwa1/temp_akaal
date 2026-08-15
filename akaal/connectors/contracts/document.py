"""
AKAAL Document Database Capability Extension Contract (P4.1).
==============================================================
Defines document database capability extension interfaces (MongoDB, Couchbase, Firestore):
- Database and collection discovery
- Document schema inference and nested field inspection
- Document batch read/write
- Change stream and resume token inspection
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IDocumentCapability(ABC):
    """Extension contract for document databases (MongoDB, Couchbase, Firestore)."""

    @abstractmethod
    async def discover_databases(self) -> List[str]:
        """Discovers database names."""
        pass

    @abstractmethod
    async def discover_collections(self, database_name: Optional[str] = None) -> List[str]:
        """Discovers collection names."""
        pass

    @abstractmethod
    async def infer_collection_schema(
        self,
        collection_name: str,
        sample_size: int = 100,
        database_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Infers document field types and structure from sample documents."""
        pass

    @abstractmethod
    async def read_documents_batch(
        self,
        collection_name: str,
        skip: int,
        limit: int,
        database_name: Optional[str] = None,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Reads batch of documents."""
        pass

    @abstractmethod
    async def write_documents_batch(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        database_name: Optional[str] = None,
    ) -> int:
        """Writes batch of documents. Returns count of inserted/updated documents."""
        pass
