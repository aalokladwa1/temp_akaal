"""Enterprise Validation Cache implementation."""

import time
import threading
from typing import Any, Dict, Optional
from akaal.validation.core.interfaces import ICache
from akaal.validation.cache.invalidation import CacheInvalidationManager


class ValidationCache(ICache):
    """In-memory enterprise cache with TTL and sub-caches for Merkle, checksum, schema, metadata, and CDC."""

    def __init__(self, default_ttl_seconds: int = 3600):
        self.default_ttl = default_ttl_seconds
        self.invalidation_mgr = CacheInvalidationManager()
        self._lock = threading.RLock()
        # Separate sub-caches for isolation
        self._sub_caches: Dict[str, Dict[str, Any]] = {
            "merkle": {},
            "checksum": {},
            "schema": {},
            "metadata": {},
            "cdc": {},
            "fingerprint": {},
        }

    def get(self, key: str) -> Optional[Any]:
        """Retrieve entry from cache if not expired."""
        with self._lock:
            if self.invalidation_mgr.is_expired(key):
                return None
            val, _ = self.invalidation_mgr._store.get(key, (None, None))
            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store item in cache with optional TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry = time.time() + ttl if ttl > 0 else None
        with self._lock:
            self.invalidation_mgr._store[key] = (value, expiry)

    def invalidate(self, key_pattern: str) -> int:
        """Invalidate keys matching pattern."""
        with self._lock:
            return self.invalidation_mgr.invalidate_by_pattern(key_pattern)

    def set_subcache(self, category: str, sub_key: str, value: Any) -> None:
        """Set a value in a specialized sub-cache (merkle, checksum, etc.)."""
        with self._lock:
            if category in self._sub_caches:
                self._sub_caches[category][sub_key] = value

    def get_subcache(self, category: str, sub_key: str) -> Optional[Any]:
        """Retrieve value from a specialized sub-cache."""
        with self._lock:
            return self._sub_caches.get(category, {}).get(sub_key)
