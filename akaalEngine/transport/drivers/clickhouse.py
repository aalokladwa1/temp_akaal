"""
akaalEngine.transport.drivers.clickhouse
===========================================
Canonical ClickHouse physical Transport driver (P7A Campaign B independence hardening).

Uses the real `clickhouse_connect` client -- `.query()` for bounded, offset-paginated reads
and `.insert()` for real columnar batch writes -- not a relabeled SQL cursor, since
clickhouse_connect's API shape (result objects with `.result_rows`/`.column_names`, a
dedicated `.insert(table, data, column_names=...)` method) is genuinely different from
Python DB-API 2.0 cursors.
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

logger = logging.getLogger("akaalEngine.transport.drivers.clickhouse")


class ClickHouseSourceReader(SourceReader):
    """Real ClickHouse SourceReader: offset-paginated `SELECT ... LIMIT ... OFFSET ...`
    via clickhouse_connect. ClickHouse has no server-side cursor, so bounded pagination via
    explicit OFFSET is the truthful mechanism -- not an unbounded `list(all_rows)`."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.client = connection_params.get("db_connection")
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
            cancellation=CancellationCapability.CLOSE_CONNECTION,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # offset-based, not an exact keyset resume
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._offset = int(last_committed_key) if last_committed_key is not None else 0
        self._exhausted = False
        if self.client is None and self.params.get("db_connection"):
            self.client = self.params["db_connection"]

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.client is None or self._exhausted or self.partition is None:
            return None
        db = self.partition.schema_name or "default"
        table = self.partition.table_name
        result = self.client.query(
            f'SELECT * FROM `{db}`.`{table}` LIMIT {int(batch_size)} OFFSET {int(self._offset)}'
        )
        rows_raw = result.result_rows
        if not rows_raw:
            self._exhausted = True
            return None
        cols = list(result.column_names)
        rows_dict = [dict(zip(cols, r)) for r in rows_raw]
        self.sequence_number += 1
        self._offset += len(rows_raw)
        meta = TransportBatchMetadata(
            batch_id=f"clickhouse-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=table,
            schema_name=db,
            sequence_number=self.sequence_number,
            row_count=len(rows_dict),
            size_bytes=sum(len(str(r)) for r in rows_raw),
        )
        if len(rows_raw) < batch_size:
            self._exhausted = True
        return TransportBatch(metadata=meta, rows=rows_dict, column_names=cols, raw_tuples=rows_raw)

    @property
    def resume_position(self) -> int:
        """The real OFFSET boundary to persist as the checkpoint's read_position."""
        return self._offset

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        pass  # client lifecycle is owned by the Connection authority, not this reader


class ClickHouseTargetWriter(TargetWriter):
    """Real ClickHouse TargetWriter using clickhouse_connect's native `.insert()` columnar
    batch-insert API. ClickHouse has no multi-statement transaction to commit/rollback --
    commit()/rollback() are truthful no-ops (each insert is already its own operation),
    matching ClickHouse's actual consistency model rather than fabricating OLTP semantics."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.client = params.get("db_connection")
        self._last_write_count = 0

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.CLOSE_CONNECTION,
            # ClickHouse has no transactional rollback; a failed insert may have partially
            # landed rows depending on block boundaries -- truthfully non-idempotent, not
            # assumed safe to blindly retry.
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,
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
        if not batch.rows:
            return 0
        if self.client is None:
            self.client = self.params.get("db_connection")
            if self.client is None:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError("ClickHouseTargetWriter has no active clickhouse_connect client.")

        cols = batch.column_names
        data = [[r.get(c) for c in cols] for r in batch.rows]
        self.client.insert(table_name, data, column_names=cols, database=target_schema)
        self._last_write_count = len(batch.rows)
        return self._last_write_count

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        # ClickHouse's eventual-consistency insert model (async inserts, replication lag on
        # ReplicatedMergeTree) makes a definitive commit check unreliable without a
        # provider-specific query_id lookup this driver does not implement -- fails closed.
        return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op: ClickHouse inserts are not part of a multi-statement transaction.
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "ClickHouseTargetWriter cannot roll back: ClickHouse has no multi-statement "
            "transaction to undo. A partially-landed insert cannot be safely reversed by this driver."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass
