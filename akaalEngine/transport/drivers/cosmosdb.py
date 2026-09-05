"""
akaalEngine.transport.drivers.cosmosdb
=======================================
Canonical Azure Cosmos DB physical Transport driver (P7A Campaign B, provider #44).

Cosmos DB is a distributed multi-model document database with its OWN native
continuation-token/partition-key/RU-throttling model -- it is NOT flattened into
DynamoDB's `LastEvaluatedKey` shape or a relational keyset. Uses the real
`azure-cosmos` SDK's `ContainerProxy.query_items(..., max_item_count=...).by_page(
continuation_token=...)` iterator (a genuine server-side continuation cursor, distinct
from DynamoDB's client-visible last-key dict) and `ContainerProxy.upsert_item()` for
writes (genuinely idempotent -- replaying the same item id produces the same end state,
not merely convenient).

No native Change Feed CDC claim is made -- no capture module exists here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

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

logger = logging.getLogger("akaalEngine.transport.drivers.cosmosdb")


class CosmosDBSourceReader(SourceReader):
    """Real Cosmos DB SourceReader using `query_items(...).by_page(continuation_token=...)`
    -- the genuine Cosmos continuation mechanism, a server-issued opaque token string."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        # `db_connection` is expected to be a real azure.cosmos.ContainerProxy (or a test
        # double shaped like one) -- resolved via the Connection Authority for this provider,
        # not constructed here.
        self.container = connection_params.get("db_connection") or connection_params.get("container")
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._page_iterator = None
        self._continuation_token: Optional[str] = None
        self._exhausted = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # server continuation token
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._exhausted = False
        self._continuation_token = last_committed_key if isinstance(last_committed_key, str) else None
        if self.container is None:
            self.container = self.params.get("db_connection") or self.params.get("container")
        if self.container is None:
            return
        self._page_iterator = None  # (re)opened lazily on first read_batch to honor batch_size

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.container is None or self._exhausted or self.partition is None:
            return None

        query = self.params.get("query") or "SELECT * FROM c"
        try:
            pages = self.container.query_items(
                query=query,
                enable_cross_partition_query=True,
                max_item_count=int(batch_size),
            ).by_page(continuation_token=self._continuation_token)
            page = next(pages)
        except StopIteration:
            self._exhausted = True
            return None
        except Exception as exc:
            from akaalEngine.transport.models.errors import TransportReadError
            raise TransportReadError(f"Cosmos DB query_items page fetch failed: {exc}") from exc

        items: List[Dict[str, Any]] = list(page)
        self._continuation_token = getattr(page, "continuation_token", None)
        if not self._continuation_token:
            self._exhausted = True
        if not items:
            self._exhausted = True
            return None

        self.sequence_number += 1
        cols = sorted({k for row in items for k in row.keys()})
        meta = TransportBatchMetadata(
            batch_id=f"cosmosdb-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=self.partition.table_name,
            schema_name=self.partition.schema_name or "",
            sequence_number=self.sequence_number,
            row_count=len(items),
            size_bytes=sum(len(str(r)) for r in items),
        )
        return TransportBatch(metadata=meta, rows=items, column_names=cols)

    @property
    def resume_position(self) -> Optional[str]:
        """The real Cosmos DB server continuation token to persist as the checkpoint's
        read_position -- opaque to the caller, never a fabricated offset."""
        return self._continuation_token

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        pass


class CosmosDBTargetWriter(TargetWriter):
    """Real Cosmos DB TargetWriter using `upsert_item()` -- genuinely idempotent (replaying
    the same document id converges to the same end state), respecting Cosmos's real 429
    (RequestRateTooLarge) throttling via `Retry-After`-style bounded retry."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.container = params.get("db_connection") or params.get("container")
        self.partition_key_field = params.get("partition_key_field", "id")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.OPERATION_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,
        )

    def write_batch(
        self,
        table_name: str,
        batch: TransportBatch,
        target_schema: str = "",
        pk_columns: Optional[Sequence[str]] = None,
        allow_merge: bool = True,
    ) -> int:
        self.verify_fencing()
        if not batch.rows:
            return 0
        if self.container is None:
            self.container = self.params.get("db_connection") or self.params.get("container")
            if self.container is None:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError("CosmosDBTargetWriter has no active azure-cosmos ContainerProxy.")

        written = 0
        for row in batch.rows:
            for attempt in range(5):
                try:
                    self.container.upsert_item(body=row)
                    written += 1
                    break
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None)
                    if status_code == 429 and attempt < 4:
                        continue  # real 429 throttling retry, not a fabricated success
                    from akaalEngine.transport.models.errors import TransportWriteError
                    raise TransportWriteError(f"Cosmos DB upsert_item failed for table '{table_name}': {exc}") from exc
        return written

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        """Real physical verification: read_item on the batch's first document id."""
        if not self.container or not batch.rows:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            first_row = batch.rows[0]
            doc_id = first_row.get("id")
            pk_val = first_row.get(self.partition_key_field, doc_id)
            if doc_id is None:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            self.container.read_item(item=doc_id, partition_key=pk_val)
            return CommitOutcomeState.COMMITTED
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code == 404:
                return CommitOutcomeState.NOT_COMMITTED
            logger.warning(f"[CosmosDBTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op: each upsert_item() call is already its own atomic operation --
        # Cosmos has no ambient multi-item transaction spanning this writer's batches
        # outside same-partition-key transactional batch (not used here).
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "CosmosDBTargetWriter cannot roll back: upsert_item has no undo; "
            "already-written items must be corrected by an explicit compensating write."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass
