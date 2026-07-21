"""
Zero-Copy Data Pipeline: StreamBuffer, BufferOwner, and MemorySlice.
Provides ownership-aware memory handling and minimal memory copies across operators.
"""

from dataclasses import dataclass, field
from threading import RLock
from typing import Optional, List, Dict, Any, Union


class BufferOwner:
    """Ownership tracker for memory slices."""
    def __init__(self, owner_id: str) -> None:
        self.owner_id = owner_id
        self._ref_count = 1
        self._lock = RLock()

    def retain(self) -> None:
        with self._lock:
            self._ref_count += 1

    def release(self) -> int:
        with self._lock:
            if self._ref_count > 0:
                self._ref_count -= 1
            return self._ref_count

    @property
    def ref_count(self) -> int:
        with self._lock:
            return self._ref_count


class MemorySlice:
    """
    Zero-copy memory slice over an underlying bytearray or object buffer.
    Provides slice borrowing without copying memory.
    """

    def __init__(
        self,
        buffer_data: Union[bytearray, bytes, List[Any]],
        offset: int = 0,
        length: Optional[int] = None,
        owner: Optional[BufferOwner] = None,
    ) -> None:
        self._buffer = buffer_data
        self._offset = offset
        self._length = length if length is not None else (len(buffer_data) - offset)
        self._owner = owner or BufferOwner("default_slice_owner")

    def slice(self, sub_offset: int, sub_length: int) -> "MemorySlice":
        """Zero-copy sub-slice borrowing."""
        if sub_offset < 0 or (sub_offset + sub_length) > self._length:
            raise IndexError("MemorySlice sub-slice out of bounds.")
        self._owner.retain()
        return MemorySlice(
            buffer_data=self._buffer,
            offset=self._offset + sub_offset,
            length=sub_length,
            owner=self._owner,
        )

    def to_bytes(self) -> bytes:
        if isinstance(self._buffer, (bytes, bytearray)):
            return bytes(self._buffer[self._offset : self._offset + self._length])
        raise ValueError("Cannot convert object list slice to bytes directly.")

    def to_list(self) -> List[Any]:
        if isinstance(self._buffer, list):
            return self._buffer[self._offset : self._offset + self._length]
        raise ValueError("Buffer is bytearray, not object list.")

    def release(self) -> None:
        self._owner.release()

    @property
    def length(self) -> int:
        return self._length

    def __len__(self) -> int:
        return self._length


class StreamBuffer:
    """
    Zero-copy stream buffer wrapping MemorySlice blocks.
    """

    def __init__(self, slice_block: MemorySlice) -> None:
        self.slice_block = slice_block

    def get_data(self) -> Union[bytes, List[Any]]:
        if isinstance(self.slice_block._buffer, (bytes, bytearray)):
            return self.slice_block.to_bytes()
        return self.slice_block.to_list()
