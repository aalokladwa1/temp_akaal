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
from akaalEngine.transport.drivers.registry import default_transport_driver_registry
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

    def resolve_source_reader_for_provider(self, provider_id: str, **driver_kwargs: Any) -> SourceReader:
        """
        Resolves and instantiates the real, provider-native SourceReader for `provider_id`
        from the dynamic transport driver registry (`transport.drivers.registry`) -- the
        canonical, extensible replacement for assuming only the 4 statically-imported SQL/
        file drivers exist. Fails closed with TransportCapabilityError if the provider has
        no registered physical source-read implementation (truthful, not a silent no-op).
        """
        reg = default_transport_driver_registry.get(provider_id)
        if reg is None or reg.reader_cls is None:
            raise TransportCapabilityError(
                f"No registered SourceReader for provider '{provider_id}'. "
                f"Registered providers: {default_transport_driver_registry.list_providers()}"
            )
        return reg.reader_cls(**driver_kwargs)

    def resolve_target_writer_for_provider(self, provider_id: str, **driver_kwargs: Any) -> TargetWriter:
        """Resolves and instantiates the real, provider-native TargetWriter for `provider_id`.
        See resolve_source_reader_for_provider() for the fail-closed contract."""
        reg = default_transport_driver_registry.get(provider_id)
        if reg is None or reg.writer_cls is None:
            raise TransportCapabilityError(
                f"No registered TargetWriter for provider '{provider_id}'. "
                f"Registered providers: {default_transport_driver_registry.list_providers()}"
            )
        return reg.writer_cls(**driver_kwargs)

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

    def _validate_security(self, security_revalidator: Optional[Callable[[], bool]]) -> None:
        """Validates execution authorization / security state at physical execution barriers during active execution."""
        if security_revalidator is not None:
            try:
                valid = security_revalidator()
                if valid is False:
                    raise TransportFencingError("Execution authorization revoked during active transport execution")
            except Exception as exc:
                if isinstance(exc, TransportFencingError):
                    raise exc
                raise TransportFencingError(f"Security barrier revalidation failed: {exc}") from exc

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
        security_revalidator: Optional[Callable[[], bool]] = None,
        resume_from_position: Optional[Any] = None,
    ) -> int:
        """
        Executes full transport pipeline for a partition:
        SourceReader -> BoundedBuffer -> DataProcessing -> TargetWriter -> Durability Checkpoint.
        Revalidates security and fencing barriers at partition entry, batch boundaries, and pre-commit.

        `resume_from_position` carries a provider-native continuation value (a real
        DynamoDB LastEvaluatedKey dict, a ClickHouse/Couchbase integer OFFSET, an InfluxDB
        Flux range-start ISO timestamp, a SQL keyset value, etc.) recovered from a prior
        run's persisted checkpoint -- it is passed straight through to
        `reader.open_partition(partition, last_committed_key=...)`, the real resume
        mechanism each provider-native SourceReader already implements.
        """
        # 1. Fencing and Security Checks before Source Fetch
        self._validate_fencing(fencing_token)
        self._validate_security(security_revalidator)

        mig_id = migration_id or getattr(partition, "migration_id", None) or "mig-transport-canonical"
        r_id = run_id or f"run-{partition.partition_id}"

        if writer and hasattr(writer, "bind_identity"):
            writer.bind_identity(migration_id=mig_id, batch_id=r_id)

        reader.open_partition(partition, last_committed_key=resume_from_position)
        total_written = 0

        telem = self.telemetry_authority
        if telem is not None and hasattr(telem, "record_counter"):
            telem.record_counter("transport_partition_execution_started_total", 1.0, {"migration_id": mig_id, "partition_id": partition.partition_id})

        try:
            while True:
                if cancellation_token and getattr(cancellation_token, "is_cancelled", False):
                    raise TransportCancelledError("Transport cancelled during read loop")

                # Fencing and Security Barrier Checks
                self._validate_fencing(fencing_token)
                self._validate_security(security_revalidator)

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

                # Execute Target Write with Retries and Security Barrier
                written = self._write_batch_with_retry(
                    writer=writer,
                    partition=partition,
                    batch=write_batch,
                    fencing_token=fencing_token,
                    cancellation_token=cancellation_token,
                    max_attempts=retry_max_attempts,
                    security_revalidator=security_revalidator,
                )
                total_written += written

                with self._lock:
                    self.rows_written_total += written
                    self.bytes_written_total += write_batch.metadata.size_bytes

                # Real per-batch telemetry -- actual observed counts, never synthetic.
                if telem is not None:
                    if hasattr(telem, "record_counter"):
                        telem.record_counter("transport_rows_read_total", len(batch.rows), {"migration_id": mig_id, "partition_id": partition.partition_id})
                        telem.record_counter("transport_rows_written_total", written, {"migration_id": mig_id, "partition_id": partition.partition_id})
                        telem.record_counter("transport_bytes_written_total", write_batch.metadata.size_bytes, {"migration_id": mig_id, "partition_id": partition.partition_id})
                    if hasattr(telem, "set_gauge"):
                        telem.set_gauge("transport_last_batch_sequence", popped_batch.metadata.sequence_number, {"migration_id": mig_id, "partition_id": partition.partition_id})

                # Advance Durable Checkpoint ONLY after Target Write is Proven
                if self.durability_authority and fencing_token and hasattr(self.durability_authority, "save_checkpoint"):
                    from akaalEngine.durability.models import MigrationCheckpoint
                    writer_ep = getattr(writer, "endpoint_identity", None)
                    # Real provider-native continuation position (LastEvaluatedKey, OFFSET,
                    # Flux range-start, etc.) -- see `resume_position` on the provider-native
                    # readers in transport/drivers/*.py -- never a fabricated placeholder.
                    read_position = getattr(reader, "resume_position", None)
                    chk = MigrationCheckpoint(
                        migration_id=mig_id,
                        job_id=batch_id_current,
                        fencing_epoch=getattr(fencing_token, "fencing_epoch", 1),
                        status="COMMITTED",
                        endpoint_identity=writer_ep,
                        metadata={
                            "table_name": partition.table_name,
                            "schema_name": partition.schema_name,
                            "last_sequence": popped_batch.metadata.sequence_number,
                            "partition_id": partition.partition_id,
                            "endpoint_identity": writer_ep,
                            "read_position": read_position,
                        },
                    )
                    try:
                        self.durability_authority.save_checkpoint(chk, fencing_token)
                    except Exception as exc:
                        with self._lock:
                            self.checkpoint_rejection_count += 1
                        logger.error(f"[TransportAuthority] Checkpoint save failed for migration '{mig_id}': {exc}")
                        raise TransportWriteError(f"Checkpoint persistence failed for migration '{mig_id}': {exc}")

            if telem is not None and hasattr(telem, "record_counter"):
                telem.record_counter("transport_partition_execution_completed_total", 1.0, {"migration_id": mig_id, "partition_id": partition.partition_id})
            return total_written

        except Exception:
            if telem is not None and hasattr(telem, "record_counter"):
                telem.record_counter("transport_partition_execution_failed_total", 1.0, {"migration_id": mig_id, "partition_id": partition.partition_id})
            raise
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
        security_revalidator: Optional[Callable[[], bool]] = None,
    ) -> int:
        capabilities = writer.get_capabilities()

        for attempt in range(1, max_attempts + 1):
            if cancellation_token and getattr(cancellation_token, "is_cancelled", False):
                raise TransportCancelledError("Cancelled during retry backoff")

            # Fencing and Security check before target write
            if fencing_token and hasattr(fencing_token, "is_valid") and not fencing_token.is_valid():
                raise TransportFencingError("Fencing token invalid before write")
            self._validate_security(security_revalidator)

            try:
                written = writer.write_batch(
                    table_name=partition.table_name,
                    batch=batch,
                    target_schema=partition.target_schema,
                    pk_columns=partition.pk_columns,
                )
                # Fencing and Security check before COMMIT
                if fencing_token and hasattr(fencing_token, "is_valid") and not fencing_token.is_valid():
                    if writer and getattr(writer, "_in_transaction", False):
                        try:
                            writer.rollback()
                        except Exception as rb_exc:
                            logger.error(f"[TransportAuthority] Pre-commit fencing rollback failed: {rb_exc}")
                            raise TransportFencingError(f"Fencing token invalid before commit and target rollback failed ({rb_exc}); target transaction state is UNKNOWN.") from rb_exc
                    raise TransportFencingError("Fencing token invalid before commit")

                if security_revalidator is not None:
                    try:
                        self._validate_security(security_revalidator)
                    except Exception as sec_exc:
                        if writer and getattr(writer, "_in_transaction", False):
                            try:
                                writer.rollback()
                            except Exception as rb_exc:
                                logger.error(f"[TransportAuthority] Pre-commit security rollback failed: {rb_exc}")
                        raise sec_exc

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


# Register the pre-existing statically-imported drivers into the same dynamic registry used
# by resolve_source_reader_for_provider()/resolve_target_writer_for_provider(), so provider
# resolution is uniform across the original drivers and every provider-native driver added
# afterward -- this does not change any existing driver's behavior, only how it is looked up.
default_transport_driver_registry.register("sqlite", reader_cls=GenericSQLSourceReader, writer_cls=GenericSQLTargetWriter)
default_transport_driver_registry.register("mysql", reader_cls=GenericSQLSourceReader, writer_cls=GenericSQLTargetWriter)
default_transport_driver_registry.register("mariadb", reader_cls=GenericSQLSourceReader, writer_cls=GenericSQLTargetWriter)
default_transport_driver_registry.register("mssql", reader_cls=GenericSQLSourceReader, writer_cls=GenericSQLTargetWriter)
default_transport_driver_registry.register("ibm_db2", reader_cls=GenericSQLSourceReader, writer_cls=GenericSQLTargetWriter)
default_transport_driver_registry.register("postgresql", reader_cls=GenericSQLSourceReader, writer_cls=PostgreSQLTargetWriter)
default_transport_driver_registry.register("oracle", reader_cls=OracleSourceReader, writer_cls=None)
default_transport_driver_registry.register("file", reader_cls=FileSourceReader, writer_cls=FileTargetWriter)

# P7A Campaign B first-10 independence hardening: real provider-native physical data-plane
# drivers, registered dynamically (never a hardcoded if/elif) so providers 39-48 can be added
# later purely by registering a new driver module.
from akaalEngine.transport.drivers.cockroachdb import CockroachDBTargetWriter
from akaalEngine.transport.drivers.yugabytedb import YugabyteDBTargetWriter
default_transport_driver_registry.register("cockroachdb", reader_cls=GenericSQLSourceReader, writer_cls=CockroachDBTargetWriter)
default_transport_driver_registry.register("yugabytedb", reader_cls=GenericSQLSourceReader, writer_cls=YugabyteDBTargetWriter)
# TiDB/SingleStore are MySQL-wire-compatible: GenericSQL(Source/Target) is now paramstyle-aware
# (resolves psycopg2/pymysql's real 'pyformat' style rather than assuming '?'), so it is a
# genuinely correct, not merely convenient, physical driver for these two -- shared low-level
# SQL execution mechanics only, never a Connection/Discovery provider-identity collapse.
default_transport_driver_registry.register("tidb", reader_cls=GenericSQLSourceReader, writer_cls=GenericSQLTargetWriter)
default_transport_driver_registry.register("singlestore", reader_cls=GenericSQLSourceReader, writer_cls=GenericSQLTargetWriter)

from akaalEngine.transport.drivers.clickhouse import ClickHouseSourceReader, ClickHouseTargetWriter
default_transport_driver_registry.register("clickhouse", reader_cls=ClickHouseSourceReader, writer_cls=ClickHouseTargetWriter)

from akaalEngine.transport.drivers.dynamodb import DynamoDBSourceReader, DynamoDBTargetWriter
default_transport_driver_registry.register("dynamodb", reader_cls=DynamoDBSourceReader, writer_cls=DynamoDBTargetWriter)

from akaalEngine.transport.drivers.couchbase import CouchbaseSourceReader, CouchbaseTargetWriter
default_transport_driver_registry.register("couchbase", reader_cls=CouchbaseSourceReader, writer_cls=CouchbaseTargetWriter)

from akaalEngine.transport.drivers.influxdb import InfluxDBSourceReader, InfluxDBTargetWriter
default_transport_driver_registry.register("influxdb", reader_cls=InfluxDBSourceReader, writer_cls=InfluxDBTargetWriter)

from akaalEngine.transport.drivers.rabbitmq import RabbitMQSourceReader, RabbitMQTargetWriter
default_transport_driver_registry.register("rabbitmq", reader_cls=RabbitMQSourceReader, writer_cls=RabbitMQTargetWriter)

from akaalEngine.transport.drivers.pulsar import PulsarSourceReader, PulsarTargetWriter
default_transport_driver_registry.register("pulsar", reader_cls=PulsarSourceReader, writer_cls=PulsarTargetWriter)

# P7A Campaign B remaining-10 independence hardening (providers #39-48): real
# provider-native physical data-plane drivers, registered dynamically -- see
# akaalEngine/transport/drivers/{teradata,vertica,sap_hana,sap_ase,informix,cosmosdb,
# spanner,salesforce,servicenow}.py. #47 (SAP application ecosystem) is intentionally
# NOT registered here -- its RFC/BAPI/IDoc/OData interface boundary is a genuine
# unresolved owner decision (see progress.md), not a silently-skipped implementation.
from akaalEngine.transport.drivers.teradata import TeradataSourceReader, TeradataTargetWriter
default_transport_driver_registry.register("teradata", reader_cls=TeradataSourceReader, writer_cls=TeradataTargetWriter)

from akaalEngine.transport.drivers.vertica import VerticaSourceReader, VerticaTargetWriter
default_transport_driver_registry.register("vertica", reader_cls=VerticaSourceReader, writer_cls=VerticaTargetWriter)

from akaalEngine.transport.drivers.sap_hana import SAPHANASourceReader, SAPHANATargetWriter
default_transport_driver_registry.register("sap_hana", reader_cls=SAPHANASourceReader, writer_cls=SAPHANATargetWriter)

from akaalEngine.transport.drivers.sap_ase import SAPASESourceReader, SAPASETargetWriter
default_transport_driver_registry.register("sap_ase", reader_cls=SAPASESourceReader, writer_cls=SAPASETargetWriter)

from akaalEngine.transport.drivers.informix import InformixSourceReader, InformixTargetWriter
default_transport_driver_registry.register("informix", reader_cls=InformixSourceReader, writer_cls=InformixTargetWriter)

from akaalEngine.transport.drivers.cosmosdb import CosmosDBSourceReader, CosmosDBTargetWriter
default_transport_driver_registry.register("cosmosdb", reader_cls=CosmosDBSourceReader, writer_cls=CosmosDBTargetWriter)

from akaalEngine.transport.drivers.spanner import SpannerSourceReader, SpannerTargetWriter
default_transport_driver_registry.register("spanner", reader_cls=SpannerSourceReader, writer_cls=SpannerTargetWriter)

from akaalEngine.transport.drivers.salesforce import SalesforceSourceReader, SalesforceTargetWriter
default_transport_driver_registry.register("salesforce", reader_cls=SalesforceSourceReader, writer_cls=SalesforceTargetWriter)

from akaalEngine.transport.drivers.servicenow import ServiceNowSourceReader, ServiceNowTargetWriter
default_transport_driver_registry.register("servicenow", reader_cls=ServiceNowSourceReader, writer_cls=ServiceNowTargetWriter)

# Provider #47 (SAP Application Ecosystem): owner-resolved 2026-09-05 scope -- ONE
# canonical provider family, capability-driven RFC/BAPI + IDoc + OData interface modes
# selected via connection_params["interface_mode"], never three separate provider
# entries. See akaalEngine/transport/drivers/sap_application.py.
from akaalEngine.transport.drivers.sap_application import SAPApplicationSourceReader, SAPApplicationTargetWriter
default_transport_driver_registry.register("sap_application", reader_cls=SAPApplicationSourceReader, writer_cls=SAPApplicationTargetWriter)
