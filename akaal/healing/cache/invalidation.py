"""HealingCacheInvalidation: Manages cache TTL invalidation."""

import time
from typing import Dict


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
