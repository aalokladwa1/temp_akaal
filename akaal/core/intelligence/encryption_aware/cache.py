"""
Akaal — Encryption Strategy Cache
=================================
Thread-safe LRU cache with TTL expiration.
"""

from collections import OrderedDict
import threading
import time
from typing import Any, Dict, Optional

class EnterpriseEncryptionCache:
    """Thread-safe LRU cache with TTL checks and cache telemetry metrics."""

    def __init__(self, max_entries: int = 1000, ttl_seconds: float = 300.0) -> None:
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._expiry: Dict[str, float] = {}
        self._lock = threading.RLock()

        # Telemetry metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """Looks up an item in cache. Checks TTL and shifts to end if found."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            # Check TTL expiry
            if time.time() > self._expiry.get(key, 0.0):
                self._evict_key(key)
                self._misses += 1
                return None

            # Move key to end (LRU)
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    def put(self, key: str, value: Any) -> None:
        """Puts an item in cache and evicts oldest items if max capacity is exceeded."""
        with self._lock:
            # Overwrite if exists
            if key in self._cache:
                self._cache[key] = value
                self._expiry[key] = time.time() + self._ttl_seconds
                self._cache.move_to_end(key)
                return

            # Enforce max limit evictions
            if len(self._cache) >= self._max_entries:
                oldest_key, _ = self._cache.popitem(last=False)
                self._expiry.pop(oldest_key, None)
                self._evictions += 1

            self._cache[key] = value
            self._expiry[key] = time.time() + self._ttl_seconds

    def _evict_key(self, key: str) -> None:
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
        self._evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._expiry.clear()

    def get_statistics(self) -> Dict[str, int]:
        with self._lock:
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
            }

    def warm_cache(self, entries: Dict[str, Any]) -> None:
        """Warms the cache with initial key-value maps."""
        with self._lock:
            for k, v in entries.items():
                self.put(k, v)

    def snapshot(self) -> Dict[str, Any]:
        """Returns a snapshot of the current non-expired cache keys."""
        with self._lock:
            now = time.time()
            return {
                k: v for k, v in self._cache.items()
                if now <= self._expiry.get(k, 0.0)
            }
