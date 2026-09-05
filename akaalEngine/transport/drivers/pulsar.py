"""
akaalEngine.transport.drivers.pulsar
=======================================
Canonical Apache Pulsar physical Transport driver (P7A Campaign B independence hardening).

Uses real `pulsar-client` `Consumer.receive()`/`Producer.send()` -- Pulsar's genuine
message-ID/subscription/cursor model, never Kafka's topic-partition-offset model.
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

logger = logging.getLogger("akaalEngine.transport.drivers.pulsar")


class PulsarSourceReader(SourceReader):
    """Real Pulsar SourceReader using a durable `Consumer` subscription and
    `receive(timeout_millis=...)` -- cumulative-ack deferred to the next batch (same
    at-least-once rationale as RabbitMQSourceReader), keyed by Pulsar's own message ID,
    never a fabricated numeric offset."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.client = connection_params.get("db_connection")
        self.consumer = None
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._pending_messages: List[Any] = []
        self._exhausted = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.CLOSE_CONNECTION,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            # Cursor-based cumulative ack IS a genuine durable resume mechanism (unlike
            # RabbitMQ classic queues), but this driver acks deferred-by-one-batch, so it is
            # provider-resumable rather than an exact per-message resume guarantee.
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._exhausted = False
        self._pending_messages = []
        if self.client is None and self.params.get("db_connection"):
            self.client = self.params["db_connection"]
        topic = partition.table_name
        subscription = self.params.get("subscription_name", f"akaal-transport-{partition.partition_id}")
        self.consumer = self.client.subscribe(topic, subscription)

    def _ack_pending(self) -> None:
        if not self._pending_messages:
            return
        try:
            # Cumulative ack: acknowledges every message up to and including the last one
            # in the batch, the genuine Pulsar cursor-advance mechanism.
            self.consumer.acknowledge_cumulative(self._pending_messages[-1])
        except Exception as exc:
            logger.warning(f"[PulsarSourceReader] acknowledge_cumulative failed: {exc}")
        self._pending_messages = []

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.consumer is None or self._exhausted or self.partition is None:
            return None

        self._ack_pending()

        rows: List[Dict[str, Any]] = []
        messages: List[Any] = []
        timeout_ms = int(self.params.get("receive_timeout_ms", 2000))
        for _ in range(int(batch_size)):
            try:
                msg = self.consumer.receive(timeout_millis=timeout_ms)
            except Exception:
                break  # real receive timeout (no more messages currently available)
            rows.append({
                "message_id": str(msg.message_id()),
                "data": msg.data(),
                "properties": dict(msg.properties() or {}),
                "publish_timestamp": msg.publish_timestamp(),
                "partition_key": msg.partition_key(),
            })
            messages.append(msg)

        if not rows:
            self._exhausted = True
            return None

        self._pending_messages = messages
        self.sequence_number += 1
        meta = TransportBatchMetadata(
            batch_id=f"pulsar-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=self.partition.table_name,
            schema_name=self.partition.schema_name or "",
            sequence_number=self.sequence_number,
            row_count=len(rows),
            size_bytes=sum(len(r["data"] or b"") for r in rows),
        )
        # Deliberately NOT setting self._exhausted here just because this batch was smaller
        # than requested -- a partial receive() batch (each call already bounded by its own
        # per-message timeout) does not mean the topic is exhausted, only that fewer messages
        # were available within the timeout window; only a fully-empty batch (checked above)
        # is treated as end-of-stream for this partition.
        return TransportBatch(metadata=meta, rows=rows, column_names=["message_id", "data", "properties", "publish_timestamp", "partition_key"])

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        # Deliberately do NOT ack self._pending_messages here -- an interrupted run
        # redelivers its last in-flight batch (at-least-once), matching RabbitMQSourceReader.
        if self.consumer is not None:
            try:
                self.consumer.close()
            except Exception:
                pass


class PulsarTargetWriter(TargetWriter):
    """Real Pulsar TargetWriter using `Producer.send()` (synchronous, acknowledged) --
    genuine per-message send-and-acknowledge, never a fabricated fire-and-forget success."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.client = params.get("db_connection")
        self.producer = None

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.CLOSE_CONNECTION,
            idempotency=IdempotencyMode.CONDITIONALLY_IDEMPOTENT,
            resumability=ResumabilityMode.NON_RESUMABLE,
        )

    def _ensure_producer(self, topic: str) -> None:
        if self.producer is not None:
            return
        if self.client is None:
            self.client = self.params.get("db_connection")
        if self.client is None:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError("PulsarTargetWriter has no active pulsar.Client connection.")
        self.producer = self.client.create_producer(topic)

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
        self._ensure_producer(table_name)

        written = 0
        for row in batch.rows:
            data = row.get("data")
            if isinstance(data, str):
                data = data.encode("utf-8")
            # Synchronous send() blocks until the broker acknowledges -- a raised exception
            # here is a genuine send failure, not a swallowed one.
            self.producer.send(data, properties=row.get("properties") or {}, partition_key=row.get("partition_key"))
            written += 1
        return written

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        # Pulsar's synchronous send() already confirms broker receipt per-message; a
        # separate ambiguous-commit check has no additional real signal to query here.
        return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op: each send() is already synchronously acknowledged.
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "PulsarTargetWriter cannot roll back: already-acknowledged sends cannot be "
            "un-published; a compensating message would be required."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.producer is not None:
            try:
                self.producer.close()
            except Exception:
                pass
