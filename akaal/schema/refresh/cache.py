"""
AKAAL Platform 5 — Thread-Safe Metadata Cache

Provides thread-safe atomic swaps, TTL expiration, invalidation triggers, and hit ratio metrics.
"""

from dataclasses import dataclass
import threading
import time
from typing import Any, Dict, Optional, Tuple

from akaal.schema.versioning.snapshot import SchemaSnapshot


@dataclass
class CacheEntry:
    snapshot: SchemaSnapshot
    cached_at: float
    ttl_seconds: float

    def is_expired(self) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return (time.time() - self.cached_at) > self.ttl_seconds


class ThreadSafeMetadataCache:
    """Thread-safe Metadata Cache supporting atomic snapshot swaps."""

    def __init__(self, default_ttl_seconds: float = 300.0) -> None:
        self._mutex = threading.RLock()
        self.default_ttl_seconds = default_ttl_seconds
        self._current_entry: Optional[CacheEntry] = None
        self._hits = 0
        self._misses = 0

    def put(self, snapshot: SchemaSnapshot, ttl_seconds: Optional[float] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        entry = CacheEntry(snapshot=snapshot, cached_at=time.time(), ttl_seconds=ttl)
        with self._mutex:
            self._current_entry = entry

    def get(self) -> Optional[SchemaSnapshot]:
        with self._mutex:
            if self._current_entry is None or self._current_entry.is_expired():
                self._misses += 1
                return None
            self._hits += 1
            return self._current_entry.snapshot

    def invalidate(self) -> None:
        with self._mutex:
            self._current_entry = None

    def get_hit_ratio(self) -> float:
        with self._mutex:
            total = self._hits + self._misses
            return self._hits / total if total > 0 else 1.0
