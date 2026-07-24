"""HealingTaskLeaseManager and HealingHeartbeatMonitor."""

import time
import threading
from typing import Dict, Tuple, List


class HealingTaskLeaseManager:
    def __init__(self, default_ttl_seconds: int = 30):
        self.ttl = default_ttl_seconds
        self._leases: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.RLock()

    def acquire_lease(self, task_id: str, worker_id: str) -> bool:
        with self._lock:
            if task_id in self._leases:
                w, exp = self._leases[task_id]
                if w != worker_id and time.time() < exp:
                    return False
            self._leases[task_id] = (worker_id, time.time() + self.ttl)
            return True

    def release_lease(self, task_id: str, worker_id: str) -> None:
        with self._lock:
            if task_id in self._leases and self._leases[task_id][0] == worker_id:
                del self._leases[task_id]


class HealingHeartbeatMonitor:
    def __init__(self, timeout_seconds: int = 15):
        self.timeout = timeout_seconds
        self._heartbeats: Dict[str, float] = {}
        self._lock = threading.RLock()

    def record_heartbeat(self, worker_id: str) -> None:
        with self._lock:
            self._heartbeats[worker_id] = time.time()
