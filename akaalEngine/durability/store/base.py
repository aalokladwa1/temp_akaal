"""
Base Durable Storage Backend SPI & Capabilities (DUR-001).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from akaalEngine.durability.models.state import StateRecord, StateVersion


@dataclass(frozen=True)
class StorageBackendCapabilities:
    """Capability flags advertised by a durable storage backend."""
    supports_multi_process_write: bool
    supports_network_filesystem: bool
    supports_atomic_cas: bool
    supports_transactions: bool
    supports_wal: bool


class BaseDurableStorageBackend(ABC):
    """Abstract SPI for pluggable durable storage backends."""

    @property
    @abstractmethod
    def capabilities(self) -> StorageBackendCapabilities:
        """Returns physical capabilities of the backend."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initializes backend tables, schemas, and storage files."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes connection and flushes resources."""
        pass

    @abstractmethod
    def put_state(self, record: StateRecord) -> StateVersion:
        """Persists a state record."""
        pass

    @abstractmethod
    def get_state(self, key: str, namespace: str) -> Optional[StateRecord]:
        """Retrieves a state record by key and namespace."""
        pass

    @abstractmethod
    def delete_state(self, key: str, namespace: str) -> bool:
        """Deletes a state record."""
        pass

    @abstractmethod
    def execute_transaction(self, operations: List[Any]) -> bool:
        """Executes a list of state mutations in an atomic backend transaction."""
        pass
