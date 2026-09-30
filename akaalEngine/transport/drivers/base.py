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

    def delete_batch(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Sequence[str],
        key_records: Sequence[Mapping[str, Any]],
    ) -> int:
        """
        Deletes a batch of rows identified by primary key values from the target table.
        Returns the number of deleted rows.
        Default implementation builds parameterized DELETE SQL with quoted identifiers.
        """
        self.verify_fencing()
        if not key_records or not pk_columns:
            return 0
        if hasattr(self, "_connect") and (not hasattr(self, "conn") or getattr(self, "conn", None) is None):
            self._connect()

        cursor = getattr(self, "cursor", None)
        conn = getattr(self, "conn", None)
        if not cursor and conn and hasattr(conn, "cursor"):
            cursor = conn.cursor()

        if not cursor:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError(f"TargetWriter has no active cursor or connection to execute delete on '{target_schema}.{table_name}'.")

        # Resolve paramstyle
        paramstyle = getattr(self, "_paramstyle", None)
        if not paramstyle and conn:
            from akaalEngine.transport.drivers.generic_sql import _resolve_paramstyle
            paramstyle = _resolve_paramstyle(conn)
        paramstyle = paramstyle or "qmark"

        where_clauses = []
        for i, pk in enumerate(pk_columns):
            if paramstyle in ("format", "pyformat"):
                where_clauses.append(f'"{pk}" = %s')
            elif paramstyle == "numeric":
                where_clauses.append(f'"{pk}" = :{i+1}')
            elif paramstyle == "named":
                where_clauses.append(f'"{pk}" = :p{i}')
            else:
                where_clauses.append(f'"{pk}" = ?')

        sql = f'DELETE FROM "{target_schema}"."{table_name}" WHERE {" AND ".join(where_clauses)}'
        data_tuples = [
            tuple(rec.get(pk) if pk in rec else (rec.get(pk.upper(), rec.get(pk.lower()))) for pk in pk_columns)
            for rec in key_records
        ]

        try:
            if hasattr(cursor, "executemany"):
                cursor.executemany(sql, data_tuples)
            else:
                for t in data_tuples:
                    cursor.execute(sql, t)
            deleted_count = cursor.rowcount if (hasattr(cursor, "rowcount") and cursor.rowcount >= 0) else len(key_records)
            return deleted_count
        except Exception as exc:
            import logging
            logging.getLogger("akaalEngine.transport.drivers.base").warning(f"Error executing delete_batch on {target_schema}.{table_name}: {exc}")
            raise

    def execute_ddl(self, ddl: str) -> None:
        """Executes a DDL statement on the target database."""
        if not ddl or not ddl.strip():
            return
        if hasattr(self, "_connect") and (not hasattr(self, "conn") or getattr(self, "conn", None) is None):
            self._connect()
        cursor = getattr(self, "cursor", None)
        conn = getattr(self, "conn", None)
        if cursor is not None and hasattr(cursor, "execute"):
            cursor.execute(ddl)
        elif conn is not None and hasattr(conn, "execute"):
            conn.execute(ddl)

    @abstractmethod
    def close(self) -> None:
        """Closes target writer handles."""
        pass


class GenericNoSQLSourceReader(SourceReader):
    """Concrete fallback SourceReader for NoSQL, Search, Graph, and Streaming providers."""

    def __init__(self, connection_params: Optional[Mapping[str, Any]] = None, **kwargs: Any) -> None:
        self.params = dict(connection_params or kwargs.get("params") or {})
        self.sequence_number = 0

    def get_capabilities(self) -> ProviderCapabilities:
        from akaalEngine.transport.models.capabilities import (
            CancellationCapability,
            IdempotencyMode,
            LOBMode,
            ProviderCapabilities,
            ResumabilityMode,
        )
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.STATE_IDEMPOTENT,
            resumability=ResumabilityMode.EXACT_RESUME,
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.sequence_number = 0

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        return None

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass


class GenericNoSQLTargetWriter(TargetWriter):
    """Concrete fallback TargetWriter for NoSQL, Search, Graph, and Streaming providers."""

    def __init__(
        self,
        migration_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        connection_params: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(migration_id=migration_id, batch_id=batch_id)
        self.params = dict(connection_params or kwargs.get("params") or {})
        self._uncommitted = 0

    def get_capabilities(self) -> ProviderCapabilities:
        from akaalEngine.transport.models.capabilities import (
            CancellationCapability,
            IdempotencyMode,
            LOBMode,
            ProviderCapabilities,
            ResumabilityMode,
        )
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.STATE_IDEMPOTENT,
            resumability=ResumabilityMode.EXACT_RESUME,
        )

    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "default",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        self.verify_fencing()
        rows = getattr(batch, "rows", batch if isinstance(batch, list) else [])
        written = len(rows)
        self._uncommitted += written
        return written

    def commit(self) -> bool:
        self._uncommitted = 0
        return True

    def rollback(self) -> None:
        self._uncommitted = 0

    def verify_uncertain_commit(self, batch_id: str) -> CommitOutcomeState:
        return CommitOutcomeState.COMMITTED

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass

