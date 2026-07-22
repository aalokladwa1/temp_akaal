"""
Zero Copy Memory Pipeline.
"""

from typing import Dict, Any, List, Optional
from threading import RLock
from akaal.performance.optimizers.base import PluginOptimizer


class RecycledBuffer:
    """Wrapper holding a reusable byte array/payload."""
    def __init__(self, size: int) -> None:
        self.data = bytearray(size)
        self.in_use = False


class ZeroCopyMemoryPipeline(PluginOptimizer):
    """Manages reusable memory pools and recycled shared buffers."""

    def __init__(self) -> None:
        super().__init__("memory")
        self._lock = RLock()
        self._pool: Dict[int, List[RecycledBuffer]] = {}
        self.version = "1.0.0"

    def optimize(self, metrics: Dict[str, Any], current_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None
        if not current_config.get("memory_pool_enabled", False):
            return {"memory_pool_enabled": True}
        return None

    def acquire_buffer(self, size: int) -> RecycledBuffer:
        """Borrows a buffer from the pool, preventing new object allocations."""
        with self._lock:
            if size not in self._pool:
                self._pool[size] = []
            
            for buf in self._pool[size]:
                if not buf.in_use:
                    buf.in_use = True
                    return buf

            new_buf = RecycledBuffer(size)
            new_buf.in_use = True
            self._pool[size].append(new_buf)
            return new_buf

    def release_buffer(self, buffer: RecycledBuffer) -> None:
        """Returns a buffer back to the recycle pool."""
        with self._lock:
            buffer.in_use = False
