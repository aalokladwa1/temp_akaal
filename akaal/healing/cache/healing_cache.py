"""HealingFingerprint, HealingCacheInvalidation, HealingCache."""

import hashlib
import time
import threading
from typing import Any, Dict, Optional


class HealingFingerprint:
    """Generates cryptographic fingerprints for repair plans and recommendations."""

    @staticmethod
    def generate_plan_fingerprint(plan_id: str, actions: Any) -> str:
        raw = f"{plan_id}:{str(actions)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class HealingCacheInvalidation:
    """Manages cache TTL invalidation."""

    def __init__(self):
        self._timestamps: Dict[str, float] = {}

    def set_ttl(self, key: str, ttl_seconds: int) -> None:
        self._timestamps[key] = time.time() + ttl_seconds

    def is_expired(self, key: str) -> bool:
        if key not in self._timestamps:
            return False
        return time.time() > self._timestamps[key]


class HealingCache:
    """In-memory cache for repair plans, recommendations, and verification results."""

    def __init__(self, default_ttl_seconds: int = 3600):
        self.default_ttl = default_ttl_seconds
        self._store: Dict[str, Any] = {}
        self.invalidation = HealingCacheInvalidation()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if self.invalidation.is_expired(key):
                self._store.pop(key, None)
                return None
            return self._store.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            self._store[key] = value
            self.invalidation.set_ttl(key, ttl_seconds or self.default_ttl)
