"""Distributed Experiment Coordinator, Worker Leases, Scheduler, and Worker Pool."""

import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class WorkerLease:
    lease_id: str = field(default_factory=lambda: f"lease_{uuid.uuid4().hex[:8]}")
    worker_id: str = "worker_01"
    experiment_id: str = "exp_001"
    acquired_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300.0)
    is_active: bool = True


class DistributedExperimentCoordinator:
    """Coordinates distributed execution of resilience experiments across worker nodes."""

    def __init__(self):
        self._leases: Dict[str, WorkerLease] = {}
        self._active_experiments: Dict[str, str] = {}
        self._lock = threading.RLock()

    def acquire_lease(self, worker_id: str, experiment_id: str) -> WorkerLease:
        with self._lock:
            lease = WorkerLease(worker_id=worker_id, experiment_id=experiment_id)
            self._leases[lease.lease_id] = lease
            self._active_experiments[experiment_id] = worker_id
            return lease

    def release_lease(self, lease_id: str) -> None:
        with self._lock:
            lease = self._leases.pop(lease_id, None)
            if lease:
                self._active_experiments.pop(lease.experiment_id, None)

    def get_coordinator_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_leases": len(self._leases),
                "active_experiments": len(self._active_experiments),
                "coordinator_healthy": True,
                "timestamp": time.time(),
            }
