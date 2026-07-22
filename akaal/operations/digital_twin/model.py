"""
Operational Digital Twin Model.
Maintains a real-time, thread-safe in-memory model of the cluster state.
"""

from typing import Dict, Any, List, Optional
from threading import RLock
import time


class ClusterNodeModel:
    def __init__(self, node_id: str, address: str, total_cpu: int = 16, total_memory_mb: int = 65536) -> None:
        self.node_id = node_id
        self.address = address
        self.total_cpu = total_cpu
        self.total_memory_mb = total_memory_mb
        self.status = "ACTIVE"
        self.last_heartbeat = time.time()


class WorkerModel:
    def __init__(self, worker_id: str, node_id: str, slots: int = 4) -> None:
        self.worker_id = worker_id
        self.node_id = node_id
        self.slots = slots
        self.status = "HEALTHY"
        self.assigned_jobs: List[str] = []
        self.last_heartbeat = time.time()


class ActiveJobModel:
    def __init__(self, job_id: str, workflow_id: str, assigned_worker: str = "") -> None:
        self.job_id = job_id
        self.workflow_id = workflow_id
        self.assigned_worker = assigned_worker
        self.state = "RUNNING"
        self.started_at = time.time()


class DigitalTwinModel:
    """Thread-safe state snapshot of AKAAL operations."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.nodes: Dict[str, ClusterNodeModel] = {}
        self.workers: Dict[str, WorkerModel] = {}
        self.active_jobs: Dict[str, ActiveJobModel] = {}
        self.platform_health: Dict[str, float] = {
            "Platform1": 100.0,
            "Platform2": 100.0,
            "Platform3": 100.0,
            "Platform5": 100.0,
            "Platform6": 100.0,
        }
        self.overall_health = 100.0
        self.maintenance_mode = False
        self.last_updated = time.time()

    def update_node(self, node: ClusterNodeModel) -> None:
        with self._lock:
            self.nodes[node.node_id] = node
            self.last_updated = time.time()

    def update_worker(self, worker: WorkerModel) -> None:
        with self._lock:
            self.workers[worker.worker_id] = worker
            self.last_updated = time.time()

    def update_job(self, job: ActiveJobModel) -> None:
        with self._lock:
            self.active_jobs[job.job_id] = job
            self.last_updated = time.time()

    def update_health(self, platform_id: str, health: float) -> None:
        with self._lock:
            self.platform_health[platform_id] = max(0.0, min(100.0, health))
            # Calculate overall health as weighted average
            if self.platform_health:
                self.overall_health = sum(self.platform_health.values()) / len(self.platform_health)
            self.last_updated = time.time()

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "nodes": {nid: n.status for nid, n in self.nodes.items()},
                "workers": {wid: w.status for wid, w in self.workers.items()},
                "active_jobs": {jid: j.state for jid, j in self.active_jobs.items()},
                "platform_health": dict(self.platform_health),
                "overall_health": self.overall_health,
                "maintenance_mode": self.maintenance_mode,
                "last_updated": self.last_updated
            }
