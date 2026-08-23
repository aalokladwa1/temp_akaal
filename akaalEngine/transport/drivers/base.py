"""
akaalEngine.transport.drivers.base
===================================
Abstract base classes SourceReader and TargetWriter for Authority #9 Transport.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from akaalEngine.transport.models.batch import TransportBatch
from akaalEngine.transport.models.capabilities import (
    CommitOutcomeState,
    ProviderCapabilities,
)
from akaalEngine.transport.models.spec import TransportPartition


class SourceReader(ABC):
    """Abstract interface for database and file source partition reading."""

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Returns physical capability descriptor for this reader."""
        pass

    @abstractmethod
    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        """Opens source partition query or stream cursor."""
        pass

    @abstractmethod
    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        """Reads a batch of rows from the partition. Returns None when EOF is reached."""
        pass

    @abstractmethod
    def cancel(self) -> None:
        """Cancels active reader query or operation if supported."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes reader cursor and connection handles."""
        pass


class TargetWriter(ABC):
    """Abstract interface for database and file target writing."""

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Returns physical capability descriptor for this writer."""
        pass

    @abstractmethod
    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "public",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        """Writes a batch of rows to the target. Returns number of rows inserted/updated."""
        pass

    @abstractmethod
    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Sequence[str],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        """
        Verifies whether an un-acknowledged batch committed after network timeout.
        Returns COMMITTED, NOT_COMMITTED, or UNKNOWN_COMMIT_OUTCOME.
        """
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commits current transaction."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rolls back current transaction."""
        pass

    @abstractmethod
    def cancel(self) -> None:
        """Cancels active writer operation."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes target writer handles."""
        pass
