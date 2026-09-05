"""
akaalEngine.transport.drivers.dynamodb
=========================================
Canonical AWS DynamoDB physical Transport driver (P7A Campaign B independence hardening).

Uses the real boto3 `dynamodb` client's `.scan()`/`.batch_write_item()` -- genuinely
different pagination (`LastEvaluatedKey`, not an offset or keyset) and write semantics
(25-item batch limit, `UnprocessedItems` retry) from any SQL driver.
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

logger = logging.getLogger("akaalEngine.transport.drivers.dynamodb")

_BATCH_WRITE_LIMIT = 25  # DynamoDB's hard BatchWriteItem item-count limit


def _deserialize_value(av: Dict[str, Any]) -> Any:
    """Decodes one DynamoDB AttributeValue-shaped dict ({"S": "x"}, {"N": "1"}, ...) into a
    real Python value. Implemented directly (not via `boto3.dynamodb.types`) so this
    driver's data shape is correct even when boto3 is not installed in this environment --
    silently falling back to returning the wire-format dict unchanged (as an earlier version
    of this function did on ImportError) would be exactly the kind of undetected data
    corruption the zero-fake law forbids: rows would carry `{"S": "1"}` instead of `"1"` as
    their value, with no error raised anywhere."""
    if not isinstance(av, dict) or len(av) != 1:
        return av
    (code, val), = av.items()
    if code == "S":
        return val
    if code == "N":
        return float(val) if ("." in val or "e" in val.lower()) else int(val)
    if code == "BOOL":
        return bool(val)
    if code == "NULL":
        return None
    if code == "M":
        return {k: _deserialize_value(v) for k, v in val.items()}
    if code == "L":
        return [_deserialize_value(v) for v in val]
    if code == "SS":
        return list(val)
    if code == "NS":
        return [float(v) if ("." in v or "e" in v.lower()) else int(v) for v in val]
    if code == "BS":
        return list(val)
    if code == "B":
        return val
    return av


def _serialize_value(value: Any) -> Dict[str, Any]:
    """Encodes one real Python value into a DynamoDB AttributeValue-shaped dict -- the
    real, dependency-free inverse of _deserialize_value()."""
    if value is None:
        return {"NULL": True}
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, (int, float)):
        return {"N": str(value)}
    if isinstance(value, str):
        return {"S": value}
    if isinstance(value, bytes):
        return {"B": value}
    if isinstance(value, dict):
        return {"M": {k: _serialize_value(v) for k, v in value.items()}}
    if isinstance(value, (list, tuple)):
        return {"L": [_serialize_value(v) for v in value]}
    return {"S": str(value)}


def _deserialize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _deserialize_value(v) for k, v in item.items()}


def _serialize(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _serialize_value(v) for k, v in item.items() if v is not None}


class DynamoDBSourceReader(SourceReader):
    """Real DynamoDB SourceReader using `.scan()` with `LastEvaluatedKey`-based bounded
    pagination -- the genuine DynamoDB continuation mechanism, never an offset/keyset."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.client = connection_params.get("db_connection")
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._exclusive_start_key: Optional[Dict[str, Any]] = None
        self._exhausted = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # LastEvaluatedKey, not exact-resume
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._exhausted = False
        # last_committed_key carries a serialized LastEvaluatedKey dict from a prior checkpoint.
        self._exclusive_start_key = last_committed_key if isinstance(last_committed_key, dict) else None
        if self.client is None and self.params.get("db_connection"):
            self.client = self.params["db_connection"]

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.client is None or self._exhausted or self.partition is None:
            return None

        kwargs: Dict[str, Any] = {"TableName": self.partition.table_name, "Limit": int(batch_size)}
        if self._exclusive_start_key:
            kwargs["ExclusiveStartKey"] = self._exclusive_start_key

        resp = self.client.scan(**kwargs)
        items = resp.get("Items", [])
        self._exclusive_start_key = resp.get("LastEvaluatedKey")
        if not self._exclusive_start_key:
            self._exhausted = True
        if not items:
            return None

        self.sequence_number += 1
        rows_dict = [_deserialize(item) for item in items]
        cols = sorted({k for row in rows_dict for k in row.keys()})
        meta = TransportBatchMetadata(
            batch_id=f"dynamodb-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=self.partition.table_name,
            schema_name=self.partition.schema_name or "",
            sequence_number=self.sequence_number,
            row_count=len(rows_dict),
            size_bytes=sum(len(str(r)) for r in items),
        )
        return TransportBatch(metadata=meta, rows=rows_dict, column_names=cols)

    @property
    def current_continuation_key(self) -> Optional[Dict[str, Any]]:
        """The real DynamoDB LastEvaluatedKey to persist as the checkpoint's read_position."""
        return self._exclusive_start_key

    @property
    def resume_position(self) -> Optional[Dict[str, Any]]:
        """Uniform continuation-position accessor used by TransportAuthority to populate
        the durable checkpoint's read_position -- aliases current_continuation_key."""
        return self._exclusive_start_key

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        pass


class DynamoDBTargetWriter(TargetWriter):
    """Real DynamoDB TargetWriter using `.batch_write_item()`, respecting the real 25-item
    BatchWriteItem limit and retrying real `UnprocessedItems` (throttling), not a fabricated
    always-succeeds write."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.client = params.get("db_connection")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            # PutItem-based BatchWriteItem overwrites by key -- replaying the same batch
            # produces the same end state, genuinely idempotent (not merely convenient).
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
        if self.client is None:
            self.client = self.params.get("db_connection")
            if self.client is None:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError("DynamoDBTargetWriter has no active boto3 dynamodb client.")

        written = 0
        rows = list(batch.rows)
        for chunk_start in range(0, len(rows), _BATCH_WRITE_LIMIT):
            chunk = rows[chunk_start:chunk_start + _BATCH_WRITE_LIMIT]
            request_items = {
                table_name: [{"PutRequest": {"Item": _serialize(r)}} for r in chunk]
            }
            for attempt in range(5):
                resp = self.client.batch_write_item(RequestItems=request_items)
                unprocessed = resp.get("UnprocessedItems", {})
                sent_count = len(request_items.get(table_name, []))
                unprocessed_count = len(unprocessed.get(table_name, []))
                written += sent_count - unprocessed_count
                if not unprocessed:
                    break
                request_items = unprocessed  # real UnprocessedItems retry, not a fabricated success
            else:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError(
                    f"DynamoDB batch_write_item: {len(unprocessed.get(table_name, []))} items remained "
                    f"unprocessed (throttled) after 5 retry attempts for table '{table_name}'."
                )
        return written

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        """Real physical verification: GetItem on the batch's key(s) to check presence."""
        if not self.client or not pk_columns or not batch.rows:
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
        try:
            pk_col = pk_columns[0]
            first_row = batch.rows[0]
            key_val = first_row.get(pk_col)
            if key_val is None:
                return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME
            resp = self.client.get_item(TableName=table_name, Key=_serialize({pk_col: key_val}))
            if "Item" in resp:
                return CommitOutcomeState.COMMITTED
            return CommitOutcomeState.NOT_COMMITTED
        except Exception as exc:
            logger.warning(f"[DynamoDBTargetWriter] verify_uncertain_commit physical check failed: {exc}")
            return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op: each BatchWriteItem call is already its own atomic-per-item
        # operation (no multi-statement transaction spans batches in this writer).
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "DynamoDBTargetWriter cannot roll back: BatchWriteItem has no undo; "
            "already-written items must be corrected by an explicit compensating write."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass
