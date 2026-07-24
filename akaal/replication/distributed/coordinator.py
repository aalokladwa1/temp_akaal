"""DistributedReplicationCoordinator: Manages distributed workers, leader election, and task dispatching."""

import threading
from typing import Dict, List, Optional, Any


class DistributedReplicationWorker:
    """Worker node executing distributed replication tasks."""

    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.is_leader = False
        self.is_active = True


class DistributedReplicationCoordinator:
    """Coordinates distributed worker cluster, leader election, and leases."""

    def __init__(self, num_workers: int = 4):
        self.workers: Dict[str, DistributedReplicationWorker] = {
            f"repl_worker_{i}": DistributedReplicationWorker(f"repl_worker_{i}")
            for i in range(num_workers)
        }
        self.leader_id: Optional[str] = f"repl_worker_0"
        if self.leader_id in self.workers:
            self.workers[self.leader_id].is_leader = True
        self._lock = threading.RLock()

    def get_leader(self) -> Optional[str]:
        with self._lock:
            return self.leader_id

    def elect_new_leader(self) -> str:
        with self._lock:
            for w_id, w in self.workers.items():
                if w.is_active:
                    self.leader_id = w_id
                    w.is_leader = True
                    return w_id
            return "repl_worker_0"
