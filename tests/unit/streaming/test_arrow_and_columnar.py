"""
Unit tests for ColumnarMemoryPipeline.
"""

import time
from akaal.streaming.domain.identifiers import BatchId
from akaal.streaming.domain.models import StreamRecord, StreamBatch
from akaal.streaming.memory.columnar import ColumnarMemoryPipeline


def test_columnar_memory_pipeline_conversion():
    r1 = StreamRecord(payload={"id": 1, "val": "A"}, event_time=100.0)
    r2 = StreamRecord(payload={"id": 2, "val": "B"}, event_time=101.0)
    batch = StreamBatch(batch_id=BatchId.generate(), records=[r1, r2], created_at=time.time())

    columnar = ColumnarMemoryPipeline.to_columnar_batch(batch)
    assert columnar.num_rows == 2
    assert columnar.columns["id"] == [1, 2]
    assert columnar.columns["val"] == ["A", "B"]

    reconverted = ColumnarMemoryPipeline.to_stream_batch(columnar)
    assert len(reconverted.records) == 2
    assert reconverted.records[0].payload == {"id": 1, "val": "A"}
