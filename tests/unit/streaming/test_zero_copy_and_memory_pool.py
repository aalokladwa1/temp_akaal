"""
Unit tests for Zero-copy buffer slicing and StreamMemoryPool.
"""

import pytest

from akaal.streaming.memory.buffer import MemorySlice, BufferOwner, StreamBuffer
from akaal.streaming.memory.pool import StreamMemoryPool


def test_zero_copy_memory_slice_borrowing():
    original = bytearray(b"0123456789ABCDEF")
    owner = BufferOwner("test_owner")
    slice1 = MemorySlice(original, offset=0, length=16, owner=owner)

    assert len(slice1) == 16
    assert owner.ref_count == 1

    # Borrow sub-slice without copying
    slice2 = slice1.slice(sub_offset=4, sub_length=8)
    assert slice2.to_bytes() == b"456789AB"
    assert owner.ref_count == 2

    slice2.release()
    assert owner.ref_count == 1


def test_stream_memory_pool_allocation_and_spill():
    pool = StreamMemoryPool(max_pool_size_mb=0.0001, spill_to_disk_enabled=True)  # tiny limit ~100 bytes

    # Allocation within limits or spilling
    slice_a = pool.allocate(50)
    assert len(slice_a) == 50

    # Spill to disk functionality
    spill_id = "block_99"
    spilled_data = {"key": "value", "rows": [1, 2, 3]}
    file_path = pool.spill_to_disk(spill_id, spilled_data)
    assert file_path.endswith(".spill")

    read_back = pool.read_spilled(spill_id)
    assert read_back == spilled_data
