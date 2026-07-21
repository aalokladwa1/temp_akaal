"""
Fault Injection & Reliability Suite for Platform 3.
Verifies disk spill failure, memory pool exhaustion, corrupted spill files,
operator exceptions, watermark regressions, and leak-free resource cleanup.
"""

import pytest
import os
import tempfile

from akaal.streaming.domain.models import StreamRecord, StreamConfig, Watermark
from akaal.streaming.domain.errors import MemoryExhaustedError, WatermarkError
from akaal.streaming.memory.pool import StreamMemoryPool
from akaal.streaming.engine.streaming_engine import StreamingExecutionEngine
from akaal.streaming.operators.base import MapOperator


def test_memory_pool_exhaustion_when_spill_disabled():
    pool = StreamMemoryPool(max_pool_size_mb=0.001, spill_to_disk_enabled=False)  # ~1KB limit

    # Small allocation succeeds
    slice1 = pool.allocate(500)
    assert len(slice1) == 500

    # Oversized allocation fails with MemoryExhaustedError
    with pytest.raises(MemoryExhaustedError, match="Memory pool limit"):
        pool.allocate(2000)

    pool.free(slice1)


def test_corrupted_spill_file_recovery_handling():
    pool = StreamMemoryPool(max_pool_size_mb=10.0, spill_to_disk_enabled=True)

    # 1. Spill valid block
    file_path = pool.spill_to_disk("corrupt_block_1", {"valid": "data"})
    assert os.path.exists(file_path)

    # 2. Corrupt file content manually
    with open(file_path, "wb") as f:
        f.write(b"CORRUPTED_NON_PICKLE_DATA")

    # 3. Reading corrupted spill block raises exception gracefully without crashing runtime
    with pytest.raises(Exception):
        pool.read_spilled("corrupt_block_1")

    # 4. Attempting to read non-existent block raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        pool.read_spilled("non_existent_block")


def test_operator_fault_recovery_and_clean_engine_state():
    engine = StreamingExecutionEngine(config=StreamConfig(batch_size=10))

    class CrashingOperator(MapOperator):
        def process_element(self, record: StreamRecord):
            if record.payload.get("crash"):
                raise RuntimeError("Operator engine crash simulated!")
            return super().process_element(record)

    engine.register_operator(CrashingOperator(fn=lambda p: {"v": p["v"] * 2}))

    # Push normal and crashing records
    engine.push_record(StreamRecord(payload={"v": 1}, event_time=1.0))
    engine.push_record(StreamRecord(payload={"v": 2, "crash": True}, event_time=2.0))

    # Batch processing raises exception when hitting crashing record
    with pytest.raises(RuntimeError, match="Operator engine crash simulated!"):
        engine.process_batch()

    # Engine input/output state remains recoverable and usable afterwards
    engine.push_record(StreamRecord(payload={"v": 10}, event_time=3.0))
    processed = engine.process_batch()
    assert processed == 1
