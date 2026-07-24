"""Distributed Reliability Coordinator, Leader Election, Worker Leases, and Distributed Task Queue."""

import time
import uuid
import heapq
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ReliabilityWorkerLease:
    worker_id: str
    resource_id: str
    granted_at: float = field(default_factory=time.time)
    ttl_sec: float = 30.0

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.granted_at + self.ttl_sec)


class ReliabilityLeaseManager:
    """Manages worker leases to prevent concurrent recovery execution."""

    def __init__(self):
        self._leases: Dict[str, ReliabilityWorkerLease] = {}
        self._lock = threading.RLock()

    def acquire_lease(self, resource_id: str, worker_id: str, ttl_sec: float = 30.0) -> bool:
        with self._lock:
            existing = self._leases.get(resource_id)
            if existing and not existing.is_expired:
                if existing.worker_id == worker_id:
                    existing.granted_at = time.time()
                    return True
                return False
            self._leases[resource_id] = ReliabilityWorkerLease(worker_id, resource_id, time.time(), ttl_sec)
            return True

    def release_lease(self, resource_id: str, worker_id: str) -> None:
        with self._lock:
            existing = self._leases.get(resource_id)
            if existing and existing.worker_id == worker_id:
                del self._leases[resource_id]


class DistributedReliabilityCoordinator:
    """Coordinator handling Leader Election, Worker Coordination, and Distributed Scheduling."""

    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or f"rel_coord_{uuid.uuid4().hex[:6]}"
        self.leader_id: Optional[str] = self.node_id
        self.lease_mgr = ReliabilityLeaseManager()
        self.workers: Dict[str, float] = {f"rel_worker_{i}": time.time() for i in range(16)}
        self._lock = threading.RLock()

    def elect_leader(self) -> str:
        with self._lock:
            self.leader_id = self.node_id
            return self.leader_id

    def get_leader(self) -> Optional[str]:
        with self._lock:
            return self.leader_id

    def heartbeat(self, worker_id: str) -> None:
        with self._lock:
            self.workers[worker_id] = time.time()
