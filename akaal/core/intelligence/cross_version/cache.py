"""
Akaal — Cross-Version Compatibility Thread-Safe LRU Cache
==========================================================
TTL-expiring, capacity-bounded LRU cache for compatibility
analysis result memoization. Mirrors the compression and
encryption cache implementations.
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional


class CompatibilityCache:
    """
    Thread-safe LRU cache with TTL expiration for compatibility analysis results.

    Eviction policy:
    - TTL expiry: entries are silently evicted after ttl_seconds.
    - LRU capacity: oldest entries are evicted when max_entries is exceeded.
    """

    def __init__(self, max_entries: int = 1000, ttl_seconds: float = 300.0) -> None:
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._expiry: Dict[str, float] = {}
        self._lock = threading.RLock()

        # Telemetry counters
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Returns the cached value for key, or None if absent or expired.
        Moves a live entry to the MRU position on access.
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            if time.time() > self._expiry.get(key, 0.0):
                self._evict_key(key)
                self._misses += 1
                return None

            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    def put(self, key: str, value: Any) -> None:
        """
        Inserts or updates a cache entry. Evicts the LRU entry if at capacity.
        """
        with self._lock:
            if key in self._cache:
                self._cache[key] = value
                self._expiry[key] = time.time() + self._ttl_seconds
                self._cache.move_to_end(key)
                return

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
        """Clears all entries from the cache."""
        with self._lock:
            self._cache.clear()
            self._expiry.clear()

    def get_statistics(self) -> Dict[str, int]:
        """Returns a snapshot of hit, miss, and eviction counters."""
        with self._lock:
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
            }

    def warm_cache(self, entries: Dict[str, Any]) -> None:
        """Pre-populates the cache with a batch of key-value pairs."""
        with self._lock:
            for k, v in entries.items():
                self.put(k, v)

    def snapshot(self) -> Dict[str, Any]:
        """Returns a point-in-time snapshot of all non-expired entries."""
        with self._lock:
            now = time.time()
            return {
                k: v for k, v in self._cache.items()
                if now <= self._expiry.get(k, 0.0)
            }
