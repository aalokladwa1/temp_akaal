"""
akaalEngine.transport.drivers.couchbase
==========================================
Canonical Couchbase physical Transport driver (P7A Campaign B independence hardening).

Uses real N1QL queries for bounded, `OFFSET`-paginated reads and the real KV `upsert()` API
for writes -- document/collection semantics, not relational rows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence

from akaalEngine.transport.drivers.base import SourceReader, TargetWriter
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import (
    CancellationCapability,
    CommitOutcomeState,
    IdempotencyMode,
    LOBMode,
    ProviderCapabilities,
    ResumabilityMode,
)
from akaalEngine.transport.models.spec import TransportPartition

logger = logging.getLogger("akaalEngine.transport.drivers.couchbase")


class CouchbaseSourceReader(SourceReader):
    """Real Couchbase SourceReader: bounded N1QL `SELECT d.*, META(d).id AS __doc_id FROM
    ... OFFSET ... LIMIT ...` against the bucket/scope/collection identified by the
    partition's schema_name ("scope.collection")."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.cluster = connection_params.get("db_connection")
        self.bucket_name = connection_params.get("bucket")
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._offset = 0
        self._exhausted = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # N1QL OFFSET, not an exact keyset
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._offset = int(last_committed_key) if last_committed_key is not None else 0
        self._exhausted = False
        if self.cluster is None and self.params.get("db_connection"):
            self.cluster = self.params["db_connection"]

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.cluster is None or self._exhausted or self.partition is None:
            return None
        scope, _, collection = (self.partition.schema_name or "_default._default").partition(".")
        collection = collection or "_default"
        n1ql = (
            f'SELECT META(d).id AS __doc_id, d.* FROM `{self.bucket_name}`.`{scope}`.`{collection}` AS d '
            f'LIMIT {int(batch_size)} OFFSET {int(self._offset)}'
        )
        rows = list(self.cluster.query(n1ql))
        if not rows:
            self._exhausted = True
            return None

        self.sequence_number += 1
        self._offset += len(rows)
        cols = sorted({k for row in rows for k in row.keys()})
        meta = TransportBatchMetadata(
            batch_id=f"couchbase-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=self.partition.table_name,
            schema_name=self.partition.schema_name or "",
            sequence_number=self.sequence_number,
            row_count=len(rows),
            size_bytes=sum(len(str(r)) for r in rows),
        )
        if len(rows) < batch_size:
            self._exhausted = True
        return TransportBatch(metadata=meta, rows=list(rows), column_names=cols)

    @property
    def resume_position(self) -> int:
        """The real N1QL OFFSET boundary to persist as the checkpoint's read_position."""
        return self._offset

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        pass


class CouchbaseTargetWriter(TargetWriter):
    """Real Couchbase TargetWriter using the KV `collection.upsert(doc_id, value)` API --
    genuine per-document CAS-free upsert, not a fabricated bulk insert. Document ID is taken
    from each row's `__doc_id` field when present (round-tripped from a Couchbase source),
    else a deterministic identity is derived from the configured key column."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.cluster = params.get("db_connection")
        self.bucket_name = params.get("bucket")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            # upsert() overwrites by document key -- replaying the same batch converges to
            # the same document state, genuinely idempotent.
            idempotency=IdempotencyMode.OPERATION_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,
        )

    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "_default._default",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        self.verify_fencing()
        if not batch.rows:
            return 0
        if self.cluster is None:
            self.cluster = self.params.get("db_connection")
            if self.cluster is None:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError("CouchbaseTargetWriter has no active Couchbase cluster connection.")

        scope, _, collection_name = (target_schema or "_default._default").partition(".")
        collection_name = collection_name or "_default"
        bucket = self.cluster.bucket(self.bucket_name)
        collection = bucket.scope(scope).collection(collection_name)

        written = 0
        pk_col = pk_columns[0] if pk_columns else None
        for row in batch.rows:
            doc_id = row.get("__doc_id") or (str(row.get(pk_col)) if pk_col and row.get(pk_col) is not None else None)
            if doc_id is None:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError(
                    f"CouchbaseTargetWriter cannot derive a document ID for a row in '{table_name}': "
                    f"no '__doc_id' field and no usable pk_columns."
                )
            value = {k: v for k, v in row.items() if k != "__doc_id"}
            collection.upsert(doc_id, value)
            written += 1
        return written

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        """Real physical verification: collection.get() on the first row's document ID."""
        if not self.cluster or not batch.rows:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            scope, _, collection_name = (target_schema or "_default._default").partition(".")
            collection_name = collection_name or "_default"
            bucket = self.cluster.bucket(self.bucket_name)
            collection = bucket.scope(scope).collection(collection_name)
            pk_col = pk_columns[0] if pk_columns else None
            row = batch.rows[0]
            doc_id = row.get("__doc_id") or (str(row.get(pk_col)) if pk_col and row.get(pk_col) is not None else None)
            if doc_id is None:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            collection.get(doc_id)
            return CommitOutcomeState.COMMITTED
        except Exception as exc:
            exc_name = type(exc).__name__
            if "DocumentNotFound" in exc_name:
                return CommitOutcomeState.NOT_COMMITTED
            logger.warning(f"[CouchbaseTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op: each upsert() is already its own atomic KV operation.
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "CouchbaseTargetWriter cannot roll back: KV upsert() has no multi-document "
            "transaction to undo in this driver."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass
