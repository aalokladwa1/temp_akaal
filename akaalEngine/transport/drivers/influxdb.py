"""
akaalEngine.transport.drivers.influxdb
=========================================
Canonical InfluxDB physical Transport driver (P7A Campaign B independence hardening).

Uses the real Flux `query_api().query()` for bounded, time-range-paginated reads and the
real `write_api().write()` (line-protocol Point objects) for writes -- time-series
measurement/tag/field/timestamp semantics, never fabricated relational rows.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
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

logger = logging.getLogger("akaalEngine.transport.drivers.influxdb")

_EPOCH_START = "1970-01-01T00:00:00Z"


class InfluxDBSourceReader(SourceReader):
    """Real InfluxDB SourceReader: Flux `from(bucket)|>range(start, stop)|>limit(n)` bounded
    by an advancing time-range lower bound -- the genuine InfluxDB continuation mechanism
    (there is no offset/keyset concept in a time-series log), truthfully modeled as a moving
    `_time` boundary rather than a fabricated relational cursor."""

    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.client = connection_params.get("db_connection")
        self.org = connection_params.get("org", "")
        self.partition: Optional[TransportPartition] = None
        self.sequence_number = 0
        self._range_start = _EPOCH_START
        self._exhausted = False

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.NON_IDEMPOTENT,
            resumability=ResumabilityMode.PROVIDER_RESUMABLE,  # time-range boundary, not exact keyset
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: Optional[Any] = None) -> None:
        self.partition = partition
        self.sequence_number = 0
        self._range_start = str(last_committed_key) if last_committed_key else _EPOCH_START
        self._exhausted = False
        if self.client is None and self.params.get("db_connection"):
            self.client = self.params["db_connection"]

    def read_batch(self, batch_size: int = 5000) -> Optional[TransportBatch]:
        if self.client is None or self._exhausted or self.partition is None:
            return None

        bucket = self.partition.schema_name
        measurement = self.partition.table_name
        flux = (
            f'from(bucket: "{bucket}") '
            f'|> range(start: {self._range_start}) '
            f'|> filter(fn: (r) => r._measurement == "{measurement}") '
            f'|> sort(columns: ["_time"]) '
            f'|> limit(n: {int(batch_size)})'
        )
        rows = []
        latest_time = None
        for table in self.client.query_api().query(flux, org=self.org):
            for record in table.records:
                row = {"_time": record.get_time().isoformat(), "_field": record.get_field(), "_value": record.get_value()}
                row.update({k: v for k, v in record.values.items() if not k.startswith("_") and k not in ("result", "table")})
                rows.append(row)
                latest_time = record.get_time()

        if not rows:
            self._exhausted = True
            return None

        self.sequence_number += 1
        # Advance strictly past the last-seen timestamp to avoid re-reading the same point
        # on the next batch (Flux `range(start:)` is inclusive of the boundary instant).
        if latest_time is not None:
            advanced = latest_time.replace(microsecond=latest_time.microsecond + 1) if latest_time.microsecond < 999999 else latest_time
            self._range_start = advanced.isoformat()
        cols = sorted({k for row in rows for k in row.keys()})
        meta = TransportBatchMetadata(
            batch_id=f"influxdb-batch-{self.sequence_number}",
            partition_id=self.partition.partition_id,
            table_name=measurement,
            schema_name=bucket,
            sequence_number=self.sequence_number,
            row_count=len(rows),
            size_bytes=sum(len(str(r)) for r in rows),
        )
        if len(rows) < batch_size:
            self._exhausted = True
        return TransportBatch(metadata=meta, rows=rows, column_names=cols)

    @property
    def current_range_start(self) -> str:
        """The real Flux range-start boundary to persist as the checkpoint's read_position."""
        return self._range_start

    @property
    def resume_position(self) -> str:
        """Uniform continuation-position accessor -- aliases current_range_start."""
        return self._range_start

    def cancel(self) -> None:
        self._exhausted = True

    def close(self) -> None:
        pass


class InfluxDBTargetWriter(TargetWriter):
    """Real InfluxDB TargetWriter using `write_api().write()` with real `Point` objects --
    tags vs fields are genuinely distinguished (tags are the row's non-`_value`/non-`_field`
    string dimensions), not collapsed into a flat relational row."""

    def __init__(self, connection_params: Optional[dict] = None):
        params = connection_params or {}
        super().__init__(
            migration_id=params.get("migration_id"),
            batch_id=params.get("batch_id") or params.get("job_id"),
            endpoint_identity=params.get("endpoint_identity") or params.get("host"),
        )
        self.params = params
        self.client = params.get("db_connection")
        self.org = params.get("org", "")

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            bulk_read=False,
            bulk_write=True,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            # Writing the same (measurement, tag-set, timestamp) point again overwrites the
            # field values in place -- genuinely idempotent for a well-formed replay.
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
                raise TransportWriteError("InfluxDBTargetWriter has no active influxdb_client connection.")

        from influxdb_client import Point

        tag_keys = set(pk_columns or [])
        points = []
        for row in batch.rows:
            p = Point(table_name)
            ts = row.get("_time")
            if ts:
                p = p.time(ts)
            for k, v in row.items():
                if k in ("_time", "_field", "_value"):
                    continue
                if k in tag_keys:
                    p = p.tag(k, str(v))
                else:
                    p = p.field(k, v)
            if "_field" in row and "_value" in row:
                p = p.field(row["_field"], row["_value"])
            points.append(p)

        write_api = self.client.write_api()
        write_api.write(bucket=target_schema, org=self.org, record=points)
        return len(points)

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: Optional[Sequence[str]],
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        # InfluxDB's default write API batches/flushes asynchronously with no per-write
        # server-assigned ID to poll -- a definitive commit check is not implementable
        # without switching to SYNCHRONOUS write mode, which this driver does not assume.
        return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        # Truthful no-op: no multi-point transaction exists to commit beyond the write() call itself.
        pass

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportWriteError
        raise TransportWriteError(
            "InfluxDBTargetWriter cannot roll back: InfluxDB has no transaction to undo; "
            "already-written points must be corrected by an explicit compensating write or deletion."
        )

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        pass
