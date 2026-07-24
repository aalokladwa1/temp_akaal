"""ReliabilityCache: Multi-tier thread-safe cache for health, failures, retries, policies, diagnostics, and predictions."""

import time
import threading
from typing import Dict, Any, Optional


class ReliabilityCache:
    """Thread-safe multi-tier in-memory cache for Platform 4 reliability operations."""

    def __init__(self, default_ttl_sec: float = 300.0):
        self.default_ttl_sec = default_ttl_sec
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def set(self, key: str, value: Any, ttl_sec: Optional[float] = None) -> None:
        with self._lock:
            ttl = ttl_sec if ttl_sec is not None else self.default_ttl_sec
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
            }

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            item = self._cache[key]
            if time.time() > item["expires_at"]:
                del self._cache[key]
                return None
            return item["value"]

    def invalidate(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
