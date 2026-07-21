"""
Zero-Copy Proof & Memory Lifetime Verification Suite.
Demonstrates borrowed slices, reference counting correctness, address preservation,
and zero memory duplication.
"""

import pytest
from akaal.streaming.memory.buffer import MemorySlice, BufferOwner, StreamBuffer


def test_zero_copy_address_preservation_and_borrowing():
    # 1. Create 1MB underlying bytearray
    raw_data = bytearray(b"X" * (1024 * 1024))
    raw_address = id(raw_data)

    owner = BufferOwner("master_owner")
    master_slice = MemorySlice(raw_data, offset=0, length=len(raw_data), owner=owner)

    # 2. Derive 5 sub-slices across different offsets
    sub_slices = [
        master_slice.slice(sub_offset=i * 1000, sub_length=500)
        for i in range(5)
    ]

    # Verify reference count incremented to 1 + 5 = 6
    assert owner.ref_count == 6

    # 3. Prove zero-copy by asserting memory buffer identity (id) is identical across all slices
    for s in sub_slices:
        assert id(s._buffer) == raw_address

    # 4. Mutations on underlying raw data reflect instantly in borrowed slices without copying
    raw_data[1000] = ord("Z")
    assert sub_slices[1].to_bytes()[0] == ord("Z")

    # 5. Release sub-slices and verify ref_count decrements cleanly
    for s in sub_slices:
        s.release()

    assert owner.ref_count == 1
    master_slice.release()
    assert owner.ref_count == 0


def test_reference_counting_lifetime_and_no_dangling_references():
    owner = BufferOwner("owner_lifetime")
    assert owner.ref_count == 1

    owner.retain()
    assert owner.ref_count == 2

    rem = owner.release()
    assert rem == 1

    rem = owner.release()
    assert rem == 0

    # Extra release safety (does not underflow below 0)
    rem = owner.release()
    assert rem == 0
