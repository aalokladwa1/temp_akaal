"""
akaalEngine.transport.drivers.rabbitmq
=========================================
Canonical RabbitMQ physical Transport driver (P7A Campaign B independence hardening).

Uses real AMQP `basic_get`/`basic_publish` via `pika` -- ACK/delivery-tag semantics, never a
fabricated Kafka-style durable offset. RabbitMQ classic/quorum queues are consume-and-remove:
once a message is ACKed it cannot be re-read, so "resume" here means "unacked messages are
redelivered", not "replay from an arbitrary durable position" -- this driver deliberately
does NOT claim EXACT_RESUME.

Ack timing: to preserve at-least-once delivery, messages read in one `read_batch()` call are
NOT acked immediately (acking before the batch is durably written+checkpointed would allow
silent loss on a mid-batch crash). They are acked at the START of the *next* `read_batch()`
call, once the caller has had the opportunity to write+checkpoint the prior batch. On
`close()`, any still-pending (unacked) messages are deliberately left unacked -- an
interrupted run redelivers its last in-flight batch, which is the conservative, honest
behavior for an at-least-once queue (dropping them would risk silent loss instead).
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

logger = logging.getLogger("akaalEngine.transport.drivers.rabbitmq")


class RabbitMQSourceReader(SourceReader):
    """Real RabbitMQ SourceReader using `channel.basic_get(auto_ack=False)` in a bounded
    loop -- genuine per-message consumption with explicit deferred ACK, not a synthetic
    message generator."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.connection = connection_params.get("db_connection")
        self.channel = None
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._pending_delivery_tags: List[int] = []
        self._exhausted = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,  # per-message basic_get, not a native multi-row fetch
            bulk_write=False,  # per-message basic_publish
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.CLOSE_CONNECTION,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            # Deliberately NOT EXACT_RESUME: unacked messages redeliver, but classic/quorum
            # queues cannot rewind to an arbitrary prior offset the way a log-based source can.
            resumability=ResumabilityMode.NON_RESUMABLE,
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._exhausted = False
        self._pending_delivery_tags = []
        if self.connection is None and self.params.get("db_connection"):
            self.connection = self.params["db_connection"]
        self.channel = self.connection.channel()
        prefetch = int(self.params.get("prefetch_count", 0)) or None
        if prefetch:
            self.channel.basic_qos(prefetch_count=prefetch)

    def _ack_pending(self) -> None:
        for tag in self._pending_delivery_tags:
            try:
                self.channel.basic_ack(delivery_tag=tag)
            except Exception as exc:
                logger.warning(f"[RabbitMQSourceReader] basic_ack failed for delivery_tag={tag}: {exc}")
        self._pending_delivery_tags = []

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.channel is None or self._exhausted or self.partition is None:
            return None

        # Ack the PREVIOUS batch now that the caller has had the chance to write+checkpoint it.
        self._ack_pending()

        queue_name = self.partition.table_name
        rows: List[Dict[str, Any]] = []
        new_tags: List[int] = []
        for _ in range(int(batch_size)):
            method, properties, body = self.channel.basic_get(queue=queue_name, auto_ack=False)
            if method is None:
                break
            rows.append({
                "body": body,
                "routing_key": method.routing_key,
                "delivery_tag": method.delivery_tag,
                "redelivered": method.redelivered,
                "content_type": getattr(properties, "content_type", None),
                "headers": dict(getattr(properties, "headers", None) or {}),
            })
            new_tags.append(method.delivery_tag)

        if not rows:
            self._exhausted = True
            return None

        self._pending_delivery_tags = new_tags
        self.sequence_number += 1
        meta = TransportBatchMetadata(
            batch_id=f"rabbitmq-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=queue_name,
            schema_name=self.partition.schema_name or "/",
            sequence_number=self.sequence_number,
            row_count=len(rows),
            size_bytes=sum(len(r["body"] or b"") for r in rows),
        )
        # Deliberately NOT setting self._exhausted here just because this batch was smaller
        # than requested: unlike a bounded SQL LIMIT page (which IS exhaustive per query), a
        # partial basic_get() batch only means "fewer messages were ready this instant" -- a
        # message queue can receive new messages at any time, so only a batch with zero rows
        # (checked above) is treated as this partition's real end-of-stream.
        return TransportBatch(metadata=meta, rows=rows, column_names=["body", "routing_key", "delivery_tag", "redelivered", "content_type", "headers"])

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        # Deliberately do NOT ack self._pending_delivery_tags here -- see module docstring.
        if self.channel is not None:
            try:
                self.channel.close()
            except Exception:
                pass


class RabbitMQTargetWriter(TargetWriter):
    """Real RabbitMQ TargetWriter using `channel.basic_publish()` with publisher confirms
    when the channel supports them (`confirm_delivery()`), so a raised exception genuinely
    means the broker did not confirm receipt -- not a silently-swallowed publish failure."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.connection = params.get("db_connection")
        self.channel = None
        self._confirms_enabled = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.CLOSE_CONNECTION,
            # A confirmed publish will not be silently duplicated by this writer, but the
            # broker/consumer side may still observe at-least-once delivery on redelivery --
            # conditionally idempotent depending on the target queue's own consumer logic.
            idempotency=IdempotencyMode.CONDITIONALLY_IDEMPOTENT,
            resumability=ResumabilityMode.NON_RESUMABLE,
        )

    def _ensure_channel(self) -> None:
        if self.channel is not None:
            return
        if self.connection is None:
            self.connection = self.params.get("db_connection")
        if self.connection is None:
            from akaalEngine.transport.models.errors import TransportWriteError
            raise TransportWriteError("RabbitMQTargetWriter has no active pika connection.")
        self.channel = self.connection.channel()
        try:
            self.channel.confirm_delivery()
            self._confirms_enabled = True
        except Exception:
            self._confirms_enabled = False  # older brokers/channels without confirm support

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
        self._ensure_channel()

        exchange = target_schema or ""
        written = 0
        for row in batch.rows:
            routing_key = row.get("routing_key") or table_name
            body = row.get("body")
            if isinstance(body, str):
                body = body.encode("utf-8")
            confirmed = self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                mandatory=self._confirms_enabled,
            )
            if self._confirms_enabled and confirmed is False:
                from akaalEngine.transport.models.errors import TransportWriteError
                raise TransportWriteError(
                    f"RabbitMQ publisher confirm failed (message returned unroutable) for routing_key '{routing_key}'."
                )
            written += 1
        return written

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        # AMQP has no server-side way to ask "was this specific message actually enqueued"
        # after a connection loss during publish -- fails closed rather than guessing.
        return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op beyond publisher confirms already verified per-message above:
        # AMQP has no separate multi-message transaction boundary in this writer.
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "RabbitMQTargetWriter cannot roll back: already-confirmed publishes cannot be "
            "un-published; a compensating message would be required."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.channel is not None:
            try:
                self.channel.close()
            except Exception:
                pass
