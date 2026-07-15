"""
Akaal — Enterprise Compression Cache
====================================
Thread-safe LRU cache with TTL expiration, execution statistics,
eviction tracking, warming capability, and copy-on-write snapshotting.
"""

from collections import OrderedDict
import time
import threading
from typing import Any, Dict, Optional


class CompressionCacheEntry:
    """Represents a cached strategy resolution with an expiration timestamp."""
    def __init__(self, key: Any, value: Any, expires_at: float) -> None:
        self.key = key
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        """Returns True if the current timestamp exceeds the entry expiration threshold."""
        return time.time() > self.expires_at


class EnterpriseCompressionCache:
    """Thread-safe bounded LRU cache tracking hits, misses, and evictions."""

    def __init__(self, max_entries: int = 1000, ttl_seconds: float = 300.0) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        
        # Core storage
        self._cache: OrderedDict[Any, CompressionCacheEntry] = OrderedDict()
        
        # Operational counters
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: Any) -> Optional[Any]:
        """Retrieves a cached value, checking expiration, and updates LRU positioning."""
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                self._misses += 1
                return None
                
            if entry.is_expired():
                self._cache.pop(key)
                self._evictions += 1
                self._misses += 1
                return None
                
            # Update LRU ordering
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value

    def put(self, key: Any, value: Any) -> None:
        """Saves a value in the cache, performing LRU eviction if size limits are breached."""
        with self._lock:
            expires_at = time.time() + self.ttl_seconds
            entry = CompressionCacheEntry(key, value, expires_at)
            
            if key in self._cache:
                self._cache.pop(key)
                
            self._cache[key] = entry
            
            # LRU Eviction guard
            if len(self._cache) > self.max_entries:
                # Evict oldest item (first item in OrderedDict)
                self._cache.popitem(last=False)
                self._evictions += 1

    def clear(self) -> None:
        """Clears all cached entries and resets statistics counters."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def get_statistics(self) -> Dict[str, Any]:
        """Exposes operational performance metrics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = round(self._hits / total_requests, 4) if total_requests > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "size": len(self._cache),
                "max_entries": self.max_entries,
                "hit_ratio": hit_ratio
            }

    def warm_cache(self, data: Dict[Any, Any]) -> None:
        """Warms the cache by pre-populating entries from an input mapping."""
        with self._lock:
            for k, v in data.items():
                self.put(k, v)

    def snapshot(self) -> Dict[Any, Any]:
        """Yields a shallow copy snapshot of unexpired values."""
        with self._lock:
            snap = {}
            # Clean expired items inline
            now = time.time()
            for k, entry in list(self._cache.items()):
                if entry.is_expired():
                    self._cache.pop(k)
                    self._evictions += 1
                else:
                    snap[k] = entry.value
            return snap
