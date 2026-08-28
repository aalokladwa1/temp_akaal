"""
akaalEngine.transport.drivers.base
===================================
Abstract base classes SourceReader and TargetWriter for Authority #9 Transport.
Enforces physical mutation fencing and write-once identity binding.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple

from akaalEngine.transport.models.batch import TransportBatch
from akaalEngine.transport.models.capabilities import (
    CommitOutcomeState,
    ProviderCapabilities,
)
from akaalEngine.transport.models.spec import TransportPartition


class StaleFencingEpochError(RuntimeError):
    """Raised when a physical target driver detects a stale fencing epoch."""
    pass


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
    """Abstract interface for database and file target writing with physical fencing checks."""

    def __init__(
        self,
        migration_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        endpoint_identity: Optional[str] = None,
    ) -> None:
        self._migration_id = migration_id
        self._batch_id = batch_id
        self._endpoint_identity = endpoint_identity
        self._fencing_token_envelope: Optional[Mapping[str, Any]] = None
        self._fencing_validator_fn: Optional[Callable[[int], bool]] = None

    @property
    def migration_id(self) -> Optional[str]:
        return self._migration_id

    @migration_id.setter
    def migration_id(self, val: Optional[str]) -> None:
        if self._migration_id is not None and val is not None and self._migration_id != val:
            raise ValueError(f"TargetWriter identity immutability violation: cannot rebind migration_id '{self._migration_id}' to '{val}'.")
        self._migration_id = val

    @property
    def batch_id(self) -> Optional[str]:
        return self._batch_id

    @batch_id.setter
    def batch_id(self, val: Optional[str]) -> None:
        self._batch_id = val

    @property
    def endpoint_identity(self) -> Optional[str]:
        return self._endpoint_identity

    @endpoint_identity.setter
    def endpoint_identity(self, val: Optional[str]) -> None:
        self._endpoint_identity = val

    def bind_identity(
        self,
        migration_id: str,
        batch_id: Optional[str] = None,
        endpoint_identity: Optional[str] = None,
    ) -> None:
        """Binds write-once execution migration identity, active batch ID, and endpoint identity to writer."""
        self.migration_id = migration_id
        if batch_id:
            self.batch_id = batch_id
        if endpoint_identity:
            self.endpoint_identity = endpoint_identity

    def bind_fencing_token(
        self,
        fencing_token_envelope: Any,
        validator_fn: Optional[Callable[[int], bool]] = None,
    ) -> None:
        """Binds fencing token and epoch validator function to target writer."""
        if isinstance(fencing_token_envelope, int):
            self._fencing_token_envelope = {"fencing_epoch": fencing_token_envelope}
        else:
            self._fencing_token_envelope = fencing_token_envelope
        self._fencing_validator_fn = validator_fn

    def verify_fencing(self) -> None:
        """Physical mutation fencing barrier verification."""
        if self._fencing_token_envelope is not None and self._fencing_validator_fn is not None:
            if isinstance(self._fencing_token_envelope, int):
                epoch = self._fencing_token_envelope
            elif isinstance(self._fencing_token_envelope, (dict, Mapping)):
                epoch = self._fencing_token_envelope.get("fencing_epoch", self._fencing_token_envelope.get("epoch", 1))
            else:
                epoch = getattr(self._fencing_token_envelope, "epoch", 1)
            is_valid = self._fencing_validator_fn(int(epoch))
            if not is_valid:
                raise StaleFencingEpochError(
                    f"Physical TargetWriter fencing check failed: worker epoch {epoch} is stale (Stale fencing epoch {epoch} is stale)."
                )

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
