"""Cache invalidation manager enforcing TTL and invalidation triggers."""

import time
import fnmatch
from typing import Dict, Any, Tuple, List


class CacheInvalidationManager:
    """Manages cache entry invalidation and TTL checks."""

    def __init__(self):
        # Key -> (Value, ExpirationTimeMs)
        self._store: Dict[str, Tuple[Any, float]] = {}

    def is_expired(self, key: str) -> bool:
        """Check if a cache key has expired."""
        if key not in self._store:
            return True
        _, expiry = self._store[key]
        if expiry is not None and time.time() > expiry:
            del self._store[key]
            return True
        return False

    def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate keys matching pattern (e.g. akaal:val:merkle:*)."""
        matching = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
        for k in matching:
            del self._store[k]
        return len(matching)
