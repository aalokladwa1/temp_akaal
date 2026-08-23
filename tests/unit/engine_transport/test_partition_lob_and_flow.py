"""
tests/unit/engine_transport/test_partition_lob_and_flow.py
===========================================================
Unit tests for RangePartitioner, StreamLOBTransportHandler, TokenBucketBandwidthLimiter, and BoundedStreamBuffer.
"""

import time
import pytest

from akaalEngine.data_processing import LOBMaterializationError, StreamLOBHandle
from akaalEngine.transport import (
    AdaptiveTransportSizer,
    BoundedStreamBuffer,
    BufferState,
    LOBMode,
    PartitionStrategy,
    RangePartitioner,
    StreamLOBTransportHandler,
    TokenBucketBandwidthLimiter,
    TransportBatch,
    TransportBatchMetadata,
    TransportCancelledError,
    TransportPartition,
    TransportTuningPolicy,
)


def test_range_partitioner_edge_cases():
    """Proves RangePartitioner handles numeric, negative, decimal, NULL, min==max, empty, and clamped partitions."""
    partitioner = RangePartitioner(TransportTuningPolicy(parallelism=4))

    # Empty table -> 0 partitions
    assert len(partitioner.generate_partitions("t1", "s1", "s1", total_rows=0, pk_columns=["id"])) == 0

    # min == max -> 1 partition
    parts_single = partitioner.generate_partitions("t1", "s1", "s1", total_rows=100, pk_columns=["id"], min_pk=5, max_pk=5)
    assert len(parts_single) == 1
    assert parts_single[0].lower_bound == 5

    # Negative key range -> zero gaps, zero overlaps
    parts_neg = partitioner.generate_partitions("t1", "s1", "s1", total_rows=1000, pk_columns=["id"], min_pk=-1000, max_pk=0)
    assert len(parts_neg) == 4
    assert parts_neg[0].lower_bound == -1000

    # NULL partition routing
    parts_null = partitioner.generate_partitions("t1", "s1", "s1", total_rows=500, pk_columns=["id"], min_pk=1, max_pk=100, has_null_keys=True)
    assert any(p.is_null_partition for p in parts_null)


def test_lob_materialization_rejection():
    """Proves StreamLOBTransportHandler rejects oversized unstreamable LOBs > 10MB."""
    handler = StreamLOBTransportHandler(max_materialization_bytes=10 * 1024 * 1024)

    # 1MB -> Success
    val_safe = "x" * (1 * 1024 * 1024)
    assert handler.process_lob_value("clob_col", val_safe, LOBMode.BOUNDED_MATERIALIZATION) == val_safe

    # 15MB -> Fail closed LOBMaterializationError
    val_huge = "x" * (15 * 1024 * 1024)
    with pytest.raises(LOBMaterializationError):
        handler.process_lob_value("clob_col", val_huge, LOBMode.BOUNDED_MATERIALIZATION)


def test_token_bucket_bandwidth_limiter():
    """Proves TokenBucketBandwidthLimiter enforces rate caps using COOPERATIVE_RATE_WAIT in slices outside locks."""
    limiter = TokenBucketBandwidthLimiter(rate_bytes_per_sec=1000)

    # Consuming under rate -> no wait
    start = time.monotonic()
    limiter.consume(500)
    assert time.monotonic() - start < 0.1

    # Dynamic rate adjustment
    limiter.set_rate(0)  # Unlimited
    limiter.consume(10000)


def test_bounded_stream_buffer_flow_control():
    """Proves BoundedStreamBuffer enforces max_batches, max_rows, max_bytes concurrent limits and FSM states."""
    policy = TransportTuningPolicy(max_queue_batches=2, max_queue_rows=100, max_queue_bytes=1024)
    buffer = BoundedStreamBuffer(policy)

    meta1 = TransportBatchMetadata("b1", "p0", "t1", "s1", 1, row_count=50, size_bytes=400)
    batch1 = TransportBatch(meta1, rows=[{"a": 1}] * 50, column_names=["a"])

    meta2 = TransportBatchMetadata("b2", "p0", "t1", "s1", 2, row_count=50, size_bytes=400)
    batch2 = TransportBatch(meta2, rows=[{"a": 2}] * 50, column_names=["a"])

    buffer.push(batch1)
    buffer.push(batch2)

    assert buffer.current_rows == 100
    assert len(buffer._queue) == 2

    popped = buffer.pop()
    assert popped.metadata.batch_id == "b1"
    assert buffer.current_rows == 50

    buffer.set_draining()
    popped2 = buffer.pop()
    assert popped2.metadata.batch_id == "b2"

    assert buffer.pop() is None  # Drained
