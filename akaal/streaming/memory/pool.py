"""
Memory Pooling & Spill-to-Disk Subsystem for Platform 3.
Provides reusable memory pools, bounded memory limits, and disk-spill overflow management.
"""

from threading import RLock
from typing import List, Dict, Optional, Any
import tempfile
import os
import pickle
import logging

from akaal.streaming.domain.errors import MemoryExhaustedError
from akaal.streaming.memory.buffer import MemorySlice, BufferOwner

logger = logging.getLogger("nexusforge.streaming.memory_pool")


class StreamMemoryPool:
    """
    Thread-safe Memory Pool recycling bytearray buffers and spilling excess data to disk when bounded limit is hit.
    """

    def __init__(self, max_pool_size_mb: float = 64.0, spill_to_disk_enabled: bool = True) -> None:
        self._lock = RLock()
        self._max_bytes = int(max_pool_size_mb * 1024 * 1024)
        self._allocated_bytes = 0
        self._spill_enabled = spill_to_disk_enabled
        self._free_buffers: List[bytearray] = []
        self._spill_files: Dict[str, str] = {}  # block_id -> temp_file_path
        self._allocations_count = 0
        self._pool_hits_count = 0
        self._spill_count = 0
        self._freed_count = 0

    @property
    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            total_reqs = self._allocations_count
            reuse_rate = (self._pool_hits_count / total_reqs) if total_reqs > 0 else 0.0
            return {
                "allocations_count": self._allocations_count,
                "pool_hits_count": self._pool_hits_count,
                "spill_count": self._spill_count,
                "freed_count": self._freed_count,
                "allocated_bytes": self._allocated_bytes,
                "max_bytes": self._max_bytes,
                "memory_reuse_rate": reuse_rate,
                "buffer_pool_hit_ratio": reuse_rate,
            }

    def allocate(self, size: int) -> MemorySlice:
        """Allocate or reuse a buffer block."""
        with self._lock:
            self._allocations_count += 1
            if (self._allocated_bytes + size) > self._max_bytes:
                if not self._spill_enabled:
                    raise MemoryExhaustedError(
                        f"Memory pool limit ({self._max_bytes} bytes) exceeded. Cannot allocate {size} bytes."
                    )
                logger.warning(f"Memory pool threshold exceeded. Allocation of {size} bytes requiring disk spill management.")

            # Attempt buffer reuse
            buf = None
            for b in list(self._free_buffers):
                if len(b) >= size:
                    self._free_buffers.remove(b)
                    buf = b
                    self._pool_hits_count += 1
                    break

            if buf is None:
                buf = bytearray(size)

            self._allocated_bytes += size
            owner = BufferOwner("pool_allocator")
            return MemorySlice(buffer_data=buf, offset=0, length=size, owner=owner)

    def free(self, slice_block: MemorySlice) -> None:
        """Return memory slice buffer to pool."""
        with self._lock:
            if isinstance(slice_block._buffer, bytearray):
                self._allocated_bytes = max(0, self._allocated_bytes - slice_block.length)
                self._free_buffers.append(slice_block._buffer)
                self._freed_count += 1
            slice_block.release()

    def spill_to_disk(self, block_id: str, data: Any) -> str:
        """Spill data block to temporary disk file."""
        with self._lock:
            self._spill_count += 1
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".spill")
            try:
                pickle.dump(data, tmp)
                tmp.flush()
                file_path = tmp.name
                self._spill_files[block_id] = file_path
                return file_path
            finally:
                tmp.close()

    def read_spilled(self, block_id: str) -> Any:
        """Read back spilled data block from disk and delete temporary file."""
        with self._lock:
            file_path = self._spill_files.pop(block_id, None)
            if not file_path or not os.path.exists(file_path):
                raise FileNotFoundError(f"Spill block '{block_id}' not found on disk.")
            
            with open(file_path, "rb") as f:
                data = pickle.load(f)

            try:
                os.remove(file_path)
            except OSError:
                pass
            return data
