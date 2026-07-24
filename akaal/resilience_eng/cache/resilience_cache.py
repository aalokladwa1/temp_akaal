"""Multi-Tier Resilience Cache for experiment results, confidence scores, and reports."""

import time
import threading
from typing import Dict, Any, Optional


class ResilienceCache:
    """Thread-safe multi-tier in-memory cache for Platform 5 subsystems."""

    def __init__(self, ttl_seconds: float = 300.0):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._ttl = ttl_seconds
        self._lock = threading.RLock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            if time.time() - self._timestamps[key] > self._ttl:
                del self._cache[key]
                del self._timestamps[key]
                return None
            return self._cache[key]

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

    def size(self) -> int:
        with self._lock:
            return len(self._cache)
