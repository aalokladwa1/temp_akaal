"""Worker Node Registry and Node Capabilities Specifications."""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple
from akaal.workflow.utils.clock import IClock, SystemClock
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class WorkerCapabilities:
    """Hardware and execution capabilities of a cluster worker node."""

    cpu_cores: int = 8
    ram_mb: float = 16384.0
    gpu_count: int = 0
    node_labels: Tuple[str, ...] = field(default_factory=tuple)
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "cpu_cores": self.cpu_cores,
            "ram_mb": self.ram_mb,
            "gpu_count": self.gpu_count,
            "node_labels": list(self.node_labels),
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_cores": self.cpu_cores,
            "ram_mb": self.ram_mb,
            "gpu_count": self.gpu_count,
            "node_labels": list(self.node_labels),
            "checksum": self.checksum,
        }


@dataclass(frozen=True, slots=True)
class WorkerNode:
    """Registered cluster worker node."""

    worker_id: str
    host: str
    port: int
    capabilities: WorkerCapabilities
    active_tasks_count: int = 0
    is_draining: bool = False
    is_quarantined: bool = False
    last_heartbeat: str = "2026-01-01T00:00:00Z"
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "worker_id": self.worker_id,
            "host": self.host,
            "port": self.port,
            "capabilities": self.capabilities.to_dict(),
            "active_tasks_count": self.active_tasks_count,
            "is_draining": self.is_draining,
            "is_quarantined": self.is_quarantined,
            "last_heartbeat": self.last_heartbeat,
        }
        object.__setattr__(self, "checksum", compute_sha256(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "host": self.host,
            "port": self.port,
            "capabilities": self.capabilities.to_dict(),
            "active_tasks_count": self.active_tasks_count,
            "is_draining": self.is_draining,
            "is_quarantined": self.is_quarantined,
            "last_heartbeat": self.last_heartbeat,
            "checksum": self.checksum,
        }


class WorkerRegistry:
    """Thread-safe worker registry managing cluster worker heartbeat and status."""

    def __init__(self, clock: IClock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._workers: Dict[str, WorkerNode] = {}
        self._lock = threading.Lock()

    def register_worker(self, worker: WorkerNode) -> None:
        with self._lock:
            self._workers[worker.worker_id] = worker

    def heartbeat(self, worker_id: str, active_tasks: int) -> bool:
        with self._lock:
            w = self._workers.get(worker_id)
            if not w:
                return False
            updated = WorkerNode(
                worker_id=w.worker_id,
                host=w.host,
                port=w.port,
                capabilities=w.capabilities,
                active_tasks_count=active_tasks,
                is_draining=w.is_draining,
                is_quarantined=w.is_quarantined,
                last_heartbeat=self._clock.now_utc(),
            )
            self._workers[worker_id] = updated
            return True

    def set_draining(self, worker_id: str, draining: bool) -> None:
        with self._lock:
            w = self._workers.get(worker_id)
            if w:
                self._workers[worker_id] = WorkerNode(
                    worker_id=w.worker_id,
                    host=w.host,
                    port=w.port,
                    capabilities=w.capabilities,
                    active_tasks_count=w.active_tasks_count,
                    is_draining=draining,
                    is_quarantined=w.is_quarantined,
                    last_heartbeat=w.last_heartbeat,
                )

    def set_quarantined(self, worker_id: str, quarantined: bool) -> None:
        with self._lock:
            w = self._workers.get(worker_id)
            if w:
                self._workers[worker_id] = WorkerNode(
                    worker_id=w.worker_id,
                    host=w.host,
                    port=w.port,
                    capabilities=w.capabilities,
                    active_tasks_count=w.active_tasks_count,
                    is_draining=w.is_draining,
                    is_quarantined=quarantined,
                    last_heartbeat=w.last_heartbeat,
                )

    def list_healthy_workers(self) -> List[WorkerNode]:
        with self._lock:
            return [w for w in self._workers.values() if not w.is_draining and not w.is_quarantined]
