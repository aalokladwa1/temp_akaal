"""RepairLockManager: Resource lock manager preventing concurrent double repairs."""

import time
import threading
from typing import Dict, Tuple, Optional


class RepairLockManager:
    """Manages table/row level locks for repair operations."""

    def __init__(self, default_ttl_seconds: int = 60):
        self.default_ttl = default_ttl_seconds
        # LockKey -> (WorkerID, ExpirationTime)
        self._locks: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.RLock()

    def acquire_lock(self, resource_key: str, worker_id: str, ttl_seconds: Optional[int] = None) -> bool:
        """Acquire lock on a repair resource (e.g. table:users)."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiry = time.time() + ttl
        with self._lock:
            if resource_key in self._locks:
                owner, exp = self._locks[resource_key]
                if owner != worker_id and time.time() < exp:
                    return False  # Locked by another worker
            self._locks[resource_key] = (worker_id, expiry)
            return True

    def release_lock(self, resource_key: str, worker_id: str) -> None:
        """Release lock."""
        with self._lock:
            if resource_key in self._locks and self._locks[resource_key][0] == worker_id:
                del self._locks[resource_key]
