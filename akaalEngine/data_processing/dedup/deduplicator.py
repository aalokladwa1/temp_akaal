"""
akaalEngine.data_processing.dedup.deduplicator
===============================================
RowDeduplicator performing sliding-window composite key deduplication with bounded memory bounds.
"""

from collections import deque
import hashlib
from threading import RLock
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Set


class RowDeduplicator:
    """
    Thread-safe bounded sliding-window deduplication engine.
    Calculates deterministic hash of composite key values.
    """

    def __init__(self, max_memory_keys: int = 100000, durable_spill_checker: Optional[Callable[[str], bool]] = None) -> None:
        self.max_memory_keys = max_memory_keys
        self.durable_spill_checker = durable_spill_checker
        self._seen_keys: Set[str] = set()
        self._key_queue: deque[str] = deque(maxlen=max_memory_keys)
        self._lock = RLock()

    def _compute_key_hash(self, row: Mapping[str, Any], key_columns: Sequence[str]) -> str:
        key_vals = [str(row.get(col)) for col in key_columns]
        raw_str = "|".join(key_vals)
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def is_duplicate(self, row: Mapping[str, Any], key_columns: Sequence[str]) -> bool:
        if not key_columns:
            return False

        key_hash = self._compute_key_hash(row, key_columns)

        with self._lock:
            if key_hash in self._seen_keys:
                return True

            # If spilled to durable store check
            if len(self._seen_keys) >= self.max_memory_keys and self.durable_spill_checker:
                if self.durable_spill_checker(key_hash):
                    return True

            # Add to sliding memory window
            if len(self._key_queue) >= self.max_memory_keys:
                oldest = self._key_queue.popleft()
                self._seen_keys.discard(oldest)

            self._key_queue.append(key_hash)
            self._seen_keys.add(key_hash)
            return False

    def clear(self) -> None:
        with self._lock:
            self._seen_keys.clear()
            self._key_queue.clear()
