"""
Exhaustive Zero-Copy Proof & Memory Lifetime Suite.
Validates borrowed slices, ownership tracking, reference counting,
zero memory duplication, safe lifetime management, no dangling references,
and deep copy avoidance.
"""

import pytest
import gc
from akaal.streaming.memory.buffer import MemorySlice, BufferOwner, StreamBuffer


def test_zero_copy_exhaustive_borrowing_and_no_deep_copy():
    # Large 20MB buffer
    big_buffer = bytearray(b"0123456789" * (2 * 1024 * 1024))
    original_id = id(big_buffer)

    owner = BufferOwner("exhaustive_owner")
    root_slice = MemorySlice(big_buffer, offset=0, length=len(big_buffer), owner=owner)

    # Derive nested slices
    child_slice_1 = root_slice.slice(100, 500000)
    child_slice_2 = child_slice_1.slice(50, 100000)

    # Prove zero memory duplication: memory buffer ID is identical
    assert id(root_slice._buffer) == original_id
    assert id(child_slice_1._buffer) == original_id
    assert id(child_slice_2._buffer) == original_id

    # Reference count is 1 (root) + 1 (child1) + 1 (child2) = 3
    assert owner.ref_count == 3

    # Release child2 -> ref_count drops to 2
    child_slice_2.release()
    assert owner.ref_count == 2

    # Release child1 -> ref_count drops to 1
    child_slice_1.release()
    assert owner.ref_count == 1

    # Release root -> ref_count drops to 0
    root_slice.release()
    assert owner.ref_count == 0


def test_zero_copy_dangling_reference_safety():
    owner = BufferOwner("safety_owner")
    buf = bytearray(b"HEADER_PAYLOAD_FOOTER")

    parent_slice = MemorySlice(buf, offset=0, length=len(buf), owner=owner)
    child_slice = parent_slice.slice(7, 7)  # "PAYLOAD"

    # Delete parent_slice reference from Python namespace
    del parent_slice
    gc.collect()

    # Child slice remains valid and accessible without dangling memory pointer error
    assert child_slice.to_bytes() == b"PAYLOAD"
    assert owner.ref_count == 2  # Owner ref count holds child slice

    child_slice.release()
    assert owner.ref_count == 1
