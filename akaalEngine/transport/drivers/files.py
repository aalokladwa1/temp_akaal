"""
akaalEngine.transport.drivers.files
====================================
FileSourceReader and FileTargetWriter for CSV, JSONL, and Parquet datasets.
"""

import csv
import json
import logging
from typing import Any, Dict, List, Optional

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    _HAS_PYARROW = True
except ImportError:
    pa = None
    pq = None
    _HAS_PYARROW = False

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
from akaalEngine.transport.models.errors import TransportCapabilityError
from akaalEngine.transport.models.spec import TransportPartition

logger = logging.getLogger("akaalEngine.transport.drivers.files")


class FileSourceReader(SourceReader):
    """FileSourceReader reading CSV, JSONL, or Parquet files."""

    def __init__(self, file_path: str, format_type: str = "CSV"):
        self.file_path = file_path
        self.format_type = format_type.upper()
        self.file_handle = None
        self.sequence_number = 0

    def get_capabilities(self) -> ProviderCapabilities:
        res_mode = (
            ResumabilityMode.EXACT_RESUME
            if self.format_type in ("CSV", "JSONL")
            else (ResumabilityMode.EXACT_RESUME if _HAS_PYARROW else ResumabilityMode.NON_RESUMABLE)
        )
        return ProviderCapabilities(
            bulk_read=True,
            bulk_write=False,
            lob_read=LOBMode.BOUNDED_MATERIALIZATION,
            lob_write=LOBMode.BOUNDED_MATERIALIZATION,
            cancellation=CancellationCapability.COOPERATIVE_STOP,
            idempotency=IdempotencyMode.STATE_IDEMPOTENT,
            resumability=res_mode,
        )

    def open_partition(self, partition: TransportPartition, last_committed_key: None = None) -> None:
        self.sequence_number = 0
        if self.format_type in ("CSV", "JSONL"):
            self.file_handle = open(self.file_path, "r", encoding="utf-8")
            if self.format_type == "CSV":
                self.csv_reader = csv.DictReader(self.file_handle)

    def read_batch(self, batch_size: int = 5000) -> None:
        if self.format_type == "CSV":
            rows = []
            for _ in range(batch_size):
                try:
                    row = next(self.csv_reader)
                    rows.append(dict(row))
                except StopIteration:
                    break
            if not rows:
                return None
            self.sequence_number += 1
            cols = list(rows[0].keys())
            meta = TransportBatchMetadata(
                batch_id=f"file-batch-{self.sequence_number}",
                partition_id="p0",
                table_name=self.file_path,
                schema_name="file",
                sequence_number=self.sequence_number,
                row_count=len(rows),
                size_bytes=sum(len(str(r)) for r in rows),
            )
            return TransportBatch(metadata=meta, rows=rows, column_names=cols)

        elif self.format_type == "JSONL":
            rows = []
            for _ in range(batch_size):
                line = self.file_handle.readline()
                if not line:
                    break
                if line.strip():
                    rows.append(json.loads(line))
            if not rows:
                return None
            self.sequence_number += 1
            cols = list(rows[0].keys())
            meta = TransportBatchMetadata(
                batch_id=f"jsonl-batch-{self.sequence_number}",
                partition_id="p0",
                table_name=self.file_path,
                schema_name="file",
                sequence_number=self.sequence_number,
                row_count=len(rows),
                size_bytes=sum(len(str(r)) for r in rows),
            )
            return TransportBatch(metadata=meta, rows=rows, column_names=cols)

        elif self.format_type == "PARQUET":
            if not _HAS_PYARROW:
                raise TransportCapabilityError("PyArrow is required to read Parquet files.")
            # Simple PyArrow table reader
            table = pq.read_table(self.file_path)
            pydict = table.to_pydict()
            num_rows = table.num_rows
            rows = [{col: pydict[col][i] for col in pydict} for i in range(num_rows)]
            if not rows:
                return None
            cols = list(pydict.keys())
            meta = TransportBatchMetadata(
                batch_id="parquet-batch-1",
                partition_id="p0",
                table_name=self.file_path,
                schema_name="file",
                sequence_number=1,
                row_count=len(rows),
                size_bytes=sum(len(str(r)) for r in rows),
            )
            return TransportBatch(metadata=meta, rows=rows, column_names=cols)

        return None

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception:
                pass


class FileTargetWriter(TargetWriter):
    """FileTargetWriter writing CSV or JSONL files."""

    def __init__(
        self,
        file_path: str,
        format_type: str = "CSV",
        migration_id: Optional[str] = None,
        batch_id: Optional[str] = None,
    ):
        super().__init__(migration_id=migration_id, batch_id=batch_id, endpoint_identity=file_path)
        self.file_path = file_path
        fmt = (format_type or "CSV").upper()
        if fmt not in ("CSV", "JSONL"):
            from akaalEngine.transport.models.errors import TransportCapabilityError
            raise TransportCapabilityError(f"FileTargetWriter format '{format_type}' is not supported. Only 'CSV' and 'JSONL' formats are supported.")
        self.format_type = fmt
        self.file_handle = open(self.file_path, "w", encoding="utf-8", newline="")
        self.writer = None

    def get_capabilities(self) -> ProviderCapabilities:
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
        target_schema: str = "public",
        pk_columns: None = None,
        allow_merge: bool = True,
    ) -> int:
        if not batch.rows:
            return 0

        if self.format_type == "CSV":
            if self.writer is None:
                self.writer = csv.DictWriter(self.file_handle, fieldnames=batch.column_names)
                self.writer.writeheader()
            for r in batch.rows:
                self.writer.writerow(r)

        elif self.format_type == "JSONL":
            for r in batch.rows:
                self.file_handle.write(json.dumps(r) + "\n")

        self.file_handle.flush()
        return len(batch.rows)

    def verify_uncertain_commit(
        self,
        table_name: str,
        target_schema: str,
        pk_columns: None,
        batch: TransportBatch,
    ) -> CommitOutcomeState:
        return CommitOutcomeState.UNKNOWN_COMMIT_OUTCOME

    def commit(self) -> None:
        if self.file_handle:
            self.file_handle.flush()

    def rollback(self) -> None:
        from akaalEngine.transport.models.errors import TransportCapabilityError
        raise TransportCapabilityError("FileTargetWriter does not support physical transaction rollback for file target endpoint.")

    def cancel(self) -> None:
        pass

    def close(self) -> None:
        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception:
                pass
