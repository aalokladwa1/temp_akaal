"""
Akaal — Rule Resolution Cache
==============================
Resolution and evaluation cache for high-throughput rule decision making.
"""

import threading
from typing import Any, Dict, Optional


class RuleResolutionCache:
    """Thread-safe rule resolution cache."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: Dict[str, Any] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value

    def invalidate(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

    def clear(self) -> None:
        self.invalidate(None)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            ratio = (self._hits / total * 100.0) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total,
                "hit_ratio_percentage": round(ratio, 2),
                "cached_entries": len(self._cache),
            }
