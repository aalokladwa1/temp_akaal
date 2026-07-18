"""
Akaal — In-Memory Discovery Cache
=================================
Thread-safe in-memory cache implementation with optional TTL and persistent caching support.
"""

import time
import threading
from typing import Dict, Optional, Tuple
from akaal.scout.cache.base_cache import BaseDiscoveryCache
from akaal.scout.models.discovery_report import DiscoveryReport


class InMemoryDiscoveryCache(BaseDiscoveryCache):
    """Thread-safe in-memory Discovery cache."""

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[DiscoveryReport, Optional[float]]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[DiscoveryReport]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            report, expire_at = self._cache[key]
            if expire_at is not None and time.time() > expire_at:
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return report

    def set(self, key: str, report: DiscoveryReport, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            expire_at = (time.time() + ttl_seconds) if ttl_seconds is not None and ttl_seconds > 0 else None
            self._cache[key] = (report, expire_at)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses
