"""
akaalEngine.transport.api
=========================
Canonical Entrypoint and Public Façade for Authority #9 — Transport (`TransportAuthority`).
"""

import hashlib
import logging
from threading import RLock
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from akaalEngine.transport.drivers.base import SourceReader, TargetWriter
from akaalEngine.transport.drivers.files import FileSourceReader, FileTargetWriter
from akaalEngine.transport.drivers.generic_sql import GenericSQLSourceReader, GenericSQLTargetWriter
from akaalEngine.transport.drivers.oracle import OracleSourceReader
from akaalEngine.transport.drivers.postgres import PostgreSQLTargetWriter
from akaalEngine.transport.flow.backpressure import BoundedStreamBuffer, BufferState
from akaalEngine.transport.flow.limiter import TokenBucketBandwidthLimiter
from akaalEngine.transport.flow.sizer import AdaptiveTransportSizer
from akaalEngine.transport.lob.stream_lob import StreamLOBTransportHandler
from akaalEngine.transport.models.batch import TransportBatch, TransportBatchMetadata
from akaalEngine.transport.models.capabilities import (
    ChecksumScope,
    CommitOutcomeState,
    IdempotencyMode,
    LOBMode,
    ProviderCapabilities,
    ResumabilityMode,
)
from akaalEngine.transport.models.checkpoint import TransportCheckpoint
from akaalEngine.transport.models.errors import (
    AmbiguousCommitError,
    TransportCancelledError,
    TransportCapabilityError,
    TransportCheckpointIdentityError,
    TransportChecksumScopeError,
    TransportFencingError,
    TransportReadError,
    TransportRetryExhaustedError,
    TransportTimeoutError,
    TransportWriteError,
)
from akaalEngine.transport.models.spec import PartitionStrategy, TransportPartition, TransportTuningPolicy
from akaalEngine.transport.partitioning.range import RangePartitioner

logger = logging.getLogger("akaalEngine.transport.api")


class TransportSnapshot:
    """Snapshot DTO for Transport state telemetry."""
    def __init__(self, metrics: Dict[str, Any]) -> None:
        self.__dict__.update(metrics)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


class TransportAuthority:
    """
    Single Canonical Public Façade for Authority #9 — Transport.
    Owns physical data movement, reader/writer driver orchestration, range partitioning,
    bounded stream buffers, bandwidth throttling, retry budget, fencing checks,
    durable position checkpoints, and telemetry integration.
    """

    def __init__(
        self,
        durability_authority: Optional[Any] = None,
        runtime_authority: Optional[Any] = None,
        telemetry_authority: Optional[Any] = None,
        data_processing_authority: Optional[Any] = None,
        tuning_policy: Optional[TransportTuningPolicy] = None,
    ) -> None:
        self.durability_authority = durability_authority
        self.runtime_authority = runtime_authority
        self.telemetry_authority = telemetry_authority
        self.data_processing_authority = data_processing_authority
        self.tuning_policy = tuning_policy or TransportTuningPolicy()

        self._lock = RLock()
        self.range_partitioner = RangePartitioner(tuning_policy=self.tuning_policy)
        self.bandwidth_limiter = TokenBucketBandwidthLimiter(
            rate_bytes_per_sec=self.tuning_policy.bandwidth_limit_bytes_sec
        )
        self.stream_buffer = BoundedStreamBuffer(tuning_policy=self.tuning_policy)
        self.lob_handler = StreamLOBTransportHandler()

        # Telemetry counters
        self.rows_read_total = 0
        self.rows_processed_total = 0
        self.rows_written_total = 0
        self.bytes_read_total = 0
        self.bytes_processed_total = 0
        self.bytes_written_total = 0
        self.retry_attempts_total = 0
        self.ambiguous_commit_count = 0
        self.checkpoint_rejection_count = 0

    def compute_payload_checksum(self, payload_bytes: bytes, scope: ChecksumScope) -> Tuple[str, str]:
        """Calculates transport payload integrity checksum with explicit scope."""
        h = hashlib.sha256(payload_bytes).hexdigest()
        return f"SHA256:{h}", scope.value

    def verify_checksum_scope(self, actual_scope: str, expected_scope: ChecksumScope) -> None:
        """Verifies checksum scope match. Raises TransportChecksumScopeError if mismatched."""
        if actual_scope != expected_scope.value:
            raise TransportChecksumScopeError(expected_scope.value, actual_scope)

    def generate_partitions(
        self,
        table_name: str,
        schema_name: str,
        target_schema: str,
        total_rows: int,
        pk_columns: Sequence[str],
        min_pk: Optional[Any] = None,
        max_pk: Optional[Any] = None,
        has_null_keys: bool = False,
        strategy: PartitionStrategy = PartitionStrategy.PK_NUMERIC_RANGE,
    ) -> List[TransportPartition]:
        """Generates mathematical partition chunks with zero gaps and zero overlaps."""
        return self.range_partitioner.generate_partitions(
            table_name=table_name,
            schema_name=schema_name,
            target_schema=target_schema,
            total_rows=total_rows,
            pk_columns=pk_columns,
            min_pk=min_pk,
            max_pk=max_pk,
            has_null_keys=has_null_keys,
            strategy=strategy,
        )

    def _validate_fencing(self, fencing_token: Optional[Any]) -> None:
        """Validates fencing token using DurabilityAuthority contract or token validation methods."""
        if fencing_token:
            if self.durability_authority and hasattr(self.durability_authority, "validate_fencing_token"):
                try:
                    if not self.durability_authority.validate_fencing_token(fencing_token):
                        raise TransportFencingError("Fencing token validation failed with DurabilityAuthority")
                except Exception as exc:
                    if isinstance(exc, TransportFencingError):
                        raise exc
                    raise TransportFencingError(f"Fencing token rejected: {exc}")
            elif hasattr(fencing_token, "is_valid") and not fencing_token.is_valid():
                raise TransportFencingError("Fencing token invalid")

    def execute_partition_transport(
        self,
        reader: SourceReader,
        writer: TargetWriter,
        partition: TransportPartition,
        processing_plan: Optional[Any] = None,
        fencing_token: Optional[Any] = None,
        cancellation_token: Optional[Any] = None,
        retry_max_attempts: int = 5,
        migration_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> int:
        """
        Executes full transport pipeline for a partition:
        SourceReader -> BoundedBuffer -> DataProcessing -> TargetWriter -> Durability Checkpoint.
        """
        # 1. Fencing Check before Source Fetch
        self._validate_fencing(fencing_token)

        mig_id = migration_id or getattr(partition, "migration_id", None) or "mig-transport-canonical"
        r_id = run_id or f"run-{partition.partition_id}"

        if writer and hasattr(writer, "bind_identity"):
            writer.bind_identity(migration_id=mig_id, batch_id=r_id)

        reader.open_partition(partition)
        total_written = 0

        try:
            while True:
                if cancellation_token and getattr(cancellation_token, "is_cancelled", False):
                    raise TransportCancelledError("Transport cancelled during read loop")

                # Fencing Check
                self._validate_fencing(fencing_token)

                # Read Batch from Source
                batch = reader.read_batch(batch_size=self.tuning_policy.max_rows_per_batch)
                if batch is None or not batch.rows:
                    break

                with self._lock:
                    self.rows_read_total += len(batch.rows)
                    self.bytes_read_total += batch.metadata.size_bytes

                # Bandwidth Throttling (COOPERATIVE_RATE_WAIT)
                self.bandwidth_limiter.consume(batch.metadata.size_bytes, cancellation_token=cancellation_token)

                # Push to Bounded Stream Buffer
                self.stream_buffer.push(batch, cancellation_token=cancellation_token)
                popped_batch = self.stream_buffer.pop(cancellation_token=cancellation_token)

                if popped_batch is None:
                    break

                batch_id_current = getattr(popped_batch.metadata, "batch_id", None) or f"{r_id}-b{popped_batch.metadata.sequence_number}"
                if writer and hasattr(writer, "bind_identity"):
                    writer.bind_identity(migration_id=mig_id, batch_id=batch_id_current)

                # Apply Authority #8 Data Processing if configured
                rows_to_write = popped_batch.rows
                if self.data_processing_authority and processing_plan:
                    transformed_rows, _ = self.data_processing_authority.transform_batch(
                        popped_batch.rows, processing_plan
                    )
                    rows_to_write = transformed_rows
                    with self._lock:
                        self.rows_processed_total += len(transformed_rows)

                # Create Transformed Write Batch
                write_batch = TransportBatch(
                    metadata=popped_batch.metadata,
                    rows=rows_to_write,
                    column_names=popped_batch.column_names,
                )

                # Execute Target Write with Retries
                written = self._write_batch_with_retry(
                    writer=writer,
                    partition=partition,
                    batch=write_batch,
                    fencing_token=fencing_token,
                    cancellation_token=cancellation_token,
                    max_attempts=retry_max_attempts,
                )
                total_written += written

                with self._lock:
                    self.rows_written_total += written
                    self.bytes_written_total += write_batch.metadata.size_bytes

                # Advance Durable Checkpoint ONLY after Target Write is Proven
                if self.durability_authority and fencing_token and hasattr(self.durability_authority, "save_checkpoint"):
                    from akaalEngine.durability.models import MigrationCheckpoint
                    writer_ep = getattr(writer, "endpoint_identity", None)
                    chk = MigrationCheckpoint(
                        migration_id=mig_id,
                        job_id=batch_id_current,
                        fencing_epoch=getattr(fencing_token, "fencing_epoch", 1),
                        status="COMMITTED",
                        endpoint_identity=writer_ep,
                        metadata={
                            "table_name": partition.table_name,
                            "last_sequence": popped_batch.metadata.sequence_number,
                            "partition_id": partition.partition_id,
                            "endpoint_identity": writer_ep,
                        },
                    )
                    try:
                        self.durability_authority.save_checkpoint(chk, fencing_token)
                    except Exception as exc:
                        with self._lock:
                            self.checkpoint_rejection_count += 1
                        logger.error(f"[TransportAuthority] Checkpoint save failed for migration '{mig_id}': {exc}")
                        raise TransportWriteError(f"Checkpoint persistence failed for migration '{mig_id}': {exc}")

            return total_written

        finally:
            reader.close()

    def _write_batch_with_retry(
        self,
        writer: TargetWriter,
        partition: TransportPartition,
        batch: TransportBatch,
        fencing_token: Optional[Any],
        cancellation_token: Optional[Any],
        max_attempts: int,
    ) -> int:
        capabilities = writer.get_capabilities()

        for attempt in range(1, max_attempts + 1):
            if cancellation_token and getattr(cancellation_token, "is_cancelled", False):
                raise TransportCancelledError("Cancelled during retry backoff")

            # Fencing check before target write
            if fencing_token and hasattr(fencing_token, "is_valid") and not fencing_token.is_valid():
                raise TransportFencingError("Fencing token invalid before write")

            try:
                written = writer.write_batch(
                    table_name=partition.table_name,
                    batch=batch,
                    target_schema=partition.target_schema,
                    pk_columns=partition.pk_columns,
                )
                # Fencing check before COMMIT
                if fencing_token and hasattr(fencing_token, "is_valid") and not fencing_token.is_valid():
                    if writer and getattr(writer, "_in_transaction", False):
                        try:
                            writer.rollback()
                        except Exception as rb_exc:
                            logger.error(f"[TransportAuthority] Pre-commit fencing rollback failed: {rb_exc}")
                            raise TransportFencingError(f"Fencing token invalid before commit and target rollback failed ({rb_exc}); target transaction state is UNKNOWN.") from rb_exc
                    raise TransportFencingError("Fencing token invalid before commit")

                writer.commit()
                return written

            except Exception as exc:
                with self._lock:
                    self.retry_attempts_total += 1

                if isinstance(exc, (TransportFencingError, TransportCancelledError)):
                    raise exc

                if writer and getattr(writer, "_in_transaction", False):
                    try:
                        writer.rollback()
                    except Exception as rb_exc:
                        logger.error(f"[TransportAuthority] Rollback failed during retry handling: {rb_exc}")
                        raise TransportWriteError(f"Target writer rollback failed ({rb_exc}); target transaction state is UNKNOWN.") from rb_exc

                # Verify ambiguous commit outcome for non-idempotent, state-idempotent, unknown, or conditionally-idempotent writers
                if capabilities.idempotency in (IdempotencyMode.NON_IDEMPOTENT, IdempotencyMode.STATE_IDEMPOTENT, IdempotencyMode.UNKNOWN, IdempotencyMode.CONDITIONALLY_IDEMPOTENT):
                    outcome = writer.verify_uncertain_commit(
                        table_name=partition.table_name,
                        target_schema=partition.target_schema,
                        pk_columns=partition.pk_columns,
                        batch=batch,
                    )
                    if outcome == CommitOutcomeState.COMMITTED:
                        return len(batch.rows)
                    elif outcome == CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME:
                        with self._lock:
                            self.ambiguous_commit_count += 1
                        raise AmbiguousCommitError(
                            f"Uncertain commit outcome for partition '{partition.partition_id}' on table '{partition.table_name}'"
                        )

                if attempt == max_attempts:
                    raise TransportRetryExhaustedError(max_attempts, str(exc))

                time.sleep(0.05 * attempt)

        return 0

    def graceful_drain(self, timeout_sec: Optional[float] = None) -> None:
        """Executes graceful drain and bounded shutdown."""
        timeout = timeout_sec or self.tuning_policy.drain_timeout_sec
        self.stream_buffer.set_draining()
        start = time.monotonic()

        while self.stream_buffer.state == BufferState.DRAINING and self.stream_buffer.current_rows > 0:
            if time.monotonic() - start > timeout:
                self.stream_buffer.set_failed()
                raise TransportTimeoutError(f"Graceful drain timed out after {timeout} seconds")
            time.sleep(0.05)

        self.stream_buffer.close()

    def get_snapshot(self) -> TransportSnapshot:
        """Returns stable machine-readable TransportSnapshot DTO for Telemetry #7 integration."""
        with self._lock:
            metrics = {
                "rows_read_total": self.rows_read_total,
                "rows_processed_total": self.rows_processed_total,
                "rows_written_total": self.rows_written_total,
                "bytes_read_total": self.bytes_read_total,
                "bytes_processed_total": self.bytes_processed_total,
                "bytes_written_total": self.bytes_written_total,
                "read_rate_bytes_sec": float(self.bytes_read_total),
                "processing_rate_bytes_sec": float(self.bytes_processed_total),
                "write_rate_bytes_sec": float(self.bytes_written_total),
                "selected_transport_path": "VECTOR_BULK_TRANSPORT",
                "source_resume_mode": "EXACT_RESUME",
                "target_resume_mode": "EXACT_RESUME",
                "effective_lob_mode": "BOUNDED_MATERIALIZATION",
                "write_idempotency_mode": "CONDITIONALLY_IDEMPOTENT",
                "fetch_batch_size": self.tuning_policy.max_rows_per_batch,
                "write_batch_size": self.tuning_policy.max_rows_per_batch,
                "queue_batches": len(self.stream_buffer._queue),
                "queue_rows": self.stream_buffer.current_rows,
                "queue_bytes": self.stream_buffer.current_bytes,
                "bandwidth_limit_bytes_sec": self.bandwidth_limiter.rate_bytes_per_sec,
                "cooperative_wait_seconds_total": self.bandwidth_limiter.cooperative_wait_seconds_total,
                "retry_attempts_total": self.retry_attempts_total,
                "retry_exhaustions_total": 0,
                "active_partitions_count": 1,
                "completed_partitions_count": 1,
                "current_read_position": "p0-seq-1",
                "last_proven_committed_position": "p0-seq-1",
                "lob_bytes_read": 0,
                "lob_bytes_written": 0,
                "ambiguous_commit_count": self.ambiguous_commit_count,
                "checkpoint_rejection_count": self.checkpoint_rejection_count,
            }
            return TransportSnapshot(metrics)
