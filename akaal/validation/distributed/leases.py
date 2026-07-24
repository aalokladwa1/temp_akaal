"""TaskLeaseManager: Distributed lease allocation and lock management."""

import time
import threading
from typing import Dict, Optional


class TaskLeaseManager:
    """Manages node leases and ownership locks for distributed validation tasks."""

    def __init__(self, default_lease_seconds: int = 30):
        self.default_lease = default_lease_seconds
        # TaskID -> (WorkerID, ExpirationTime)
        self._leases: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.RLock()

    def acquire_lease(self, task_id: str, worker_id: str, lease_seconds: Optional[int] = None) -> bool:
        """Attempt to acquire or renew a lease for a task."""
        ttl = lease_seconds if lease_seconds is not None else self.default_lease
        expiry = time.time() + ttl
        with self._lock:
            if task_id in self._leases:
                current_worker, current_exp = self._leases[task_id]
                if current_worker != worker_id and time.time() < current_exp:
                    return False  # Held by active another worker
            self._leases[task_id] = (worker_id, expiry)
            return True

    def release_lease(self, task_id: str, worker_id: str) -> None:
        """Release lease if held by worker."""
        with self._lock:
            if task_id in self._leases and self._leases[task_id][0] == worker_id:
                del self._leases[task_id]

    def is_lease_valid(self, task_id: str, worker_id: str) -> bool:
        """Check if worker holds an active lease for task."""
        with self._lock:
            if task_id not in self._leases:
                return False
            w_id, exp = self._leases[task_id]
            return w_id == worker_id and time.time() < exp
