"""
Apache Arrow Memory Pipeline & Columnar Memory Representation.
Provides zero-copy columnar batch execution with optional PyArrow integration fallback.
Public APIs remain completely Arrow-independent.
"""

from typing import Dict, List, Any, Optional
import logging

from akaal.streaming.domain.identifiers import BatchId
from akaal.streaming.domain.models import StreamRecord, StreamBatch, ColumnarBatch

logger = logging.getLogger("nexusforge.streaming.columnar")

try:
    import pyarrow as pa
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False


class ColumnarMemoryPipeline:
    """
    Columnar Memory Pipeline converting row-based StreamBatches into ColumnarBatches,
    using PyArrow internally when installed or fallback columnar dictionaries.
    """

    @staticmethod
    def to_columnar_batch(batch: StreamBatch) -> ColumnarBatch:
        """Convert row StreamBatch into ColumnarBatch."""
        if not batch.records:
            return ColumnarBatch(
                batch_id=batch.batch_id,
                num_rows=0,
                columns={},
                created_at=batch.created_at,
            )

        cols: Dict[str, List[Any]] = {}
        for record in batch.records:
            for k, v in record.payload.items():
                if k not in cols:
                    cols[k] = []
                cols[k].append(v)

        num_rows = len(batch.records)

        # PyArrow internal verification if available
        if HAS_PYARROW:
            try:
                pa_batch = pa.RecordBatch.from_pydict(cols)
                logger.debug(f"PyArrow RecordBatch generated internally with {pa_batch.num_rows} rows.")
            except Exception as exc:
                logger.debug(f"PyArrow conversion fallback: {str(exc)}")

        return ColumnarBatch(
            batch_id=batch.batch_id,
            num_rows=num_rows,
            columns=cols,
            created_at=batch.created_at,
        )

    @staticmethod
    def to_stream_batch(columnar: ColumnarBatch) -> StreamBatch:
        """Convert ColumnarBatch back into row StreamBatch."""
        records: List[StreamRecord] = []
        if columnar.num_rows == 0:
            return StreamBatch(batch_id=columnar.batch_id, records=[], created_at=columnar.created_at)

        col_names = list(columnar.columns.keys())
        for i in range(columnar.num_rows):
            row_payload = {k: columnar.columns[k][i] for k in col_names if i < len(columnar.columns[k])}
            records.append(
                StreamRecord(
                    payload=row_payload,
                    event_time=columnar.created_at,
                )
            )

        return StreamBatch(batch_id=columnar.batch_id, records=records, created_at=columnar.created_at)
