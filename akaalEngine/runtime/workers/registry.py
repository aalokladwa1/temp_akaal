"""
akaalEngine.runtime.workers.registry
=====================================
WorkerRegistry managing worker registrations, status transitions, and active tasks.
Mined from `akaal/distributed/worker/registry.py`.
"""

import logging
from threading import RLock
import time
from typing import Dict, List, Optional, Sequence

from akaalEngine.runtime.models.errors import WorkerNotFoundError
from akaalEngine.runtime.models.worker import (
    WorkerSnapshot,
    WorkerSpec,
    WorkerState,
)

logger = logging.getLogger("akaalEngine.runtime.workers.registry")


class WorkerRegistry:
    """
    Thread-safe WorkerRegistry for tracking worker lifecycle, capacity, and active claims.
    """

    def __init__(self) -> None:
        self._workers: Dict[str, WorkerSpec] = {}
        self._states: Dict[str, WorkerState] = {}
        self._active_tasks: Dict[str, List[str]] = {}
        self._fencing_epochs: Dict[str, int] = {}
        self._registration_times: Dict[str, float] = {}
        self._last_heartbeats: Dict[str, float] = {}
        self._lock = RLock()

    def register_worker(self, spec: WorkerSpec, initial_fencing_epoch: int = 1) -> WorkerSnapshot:
        with self._lock:
            now = time.time()
            self._workers[spec.worker_id] = spec
            self._states[spec.worker_id] = WorkerState.AVAILABLE
            self._active_tasks[spec.worker_id] = []
            self._fencing_epochs[spec.worker_id] = initial_fencing_epoch
            self._registration_times[spec.worker_id] = now
            self._last_heartbeats[spec.worker_id] = now

            logger.info(f"[WorkerRegistry] Worker '{spec.worker_id}' registered on node '{spec.node_id}'.")
            return self.get_snapshot(spec.worker_id)

    def deregister_worker(self, worker_id: str, reason: str = "voluntary") -> None:
        with self._lock:
            if worker_id in self._workers:
                self._states[worker_id] = WorkerState.DEREGISTERED
                logger.info(f"[WorkerRegistry] Worker '{worker_id}' deregistered ({reason}).")

    def update_state(self, worker_id: str, new_state: WorkerState) -> WorkerSnapshot:
        with self._lock:
            if worker_id not in self._workers:
                raise WorkerNotFoundError(worker_id)
            self._states[worker_id] = new_state
            return self.get_snapshot(worker_id)

    def update_heartbeat(self, worker_id: str, timestamp: Optional[float] = None) -> None:
        with self._lock:
            if worker_id in self._workers:
                self._last_heartbeats[worker_id] = timestamp or time.time()

    def advance_fencing_epoch(self, worker_id: str) -> int:
        with self._lock:
            if worker_id not in self._workers:
                raise WorkerNotFoundError(worker_id)
            self._fencing_epochs[worker_id] += 1
            return self._fencing_epochs[worker_id]

    def assign_task(self, worker_id: str, task_id: str) -> None:
        with self._lock:
            if worker_id not in self._workers:
                raise WorkerNotFoundError(worker_id)
            tasks = self._active_tasks.setdefault(worker_id, [])
            if task_id not in tasks:
                tasks.append(task_id)

            spec = self._workers[worker_id]
            if len(tasks) >= spec.max_concurrency_slots:
                self._states[worker_id] = WorkerState.BUSY

    def unassign_task(self, worker_id: str, task_id: str) -> None:
        with self._lock:
            if worker_id in self._active_tasks:
                tasks = self._active_tasks[worker_id]
                if task_id in tasks:
                    tasks.remove(task_id)

                spec = self._workers.get(worker_id)
                if spec and self._states.get(worker_id) == WorkerState.BUSY:
                    if len(tasks) < spec.max_concurrency_slots:
                        self._states[worker_id] = WorkerState.AVAILABLE

    def get_snapshot(self, worker_id: str) -> WorkerSnapshot:
        with self._lock:
            if worker_id not in self._workers:
                raise WorkerNotFoundError(worker_id)
            spec = self._workers[worker_id]
            return WorkerSnapshot(
                worker_id=spec.worker_id,
                node_id=spec.node_id,
                state=self._states[spec.worker_id],
                active_task_count=len(self._active_tasks.get(spec.worker_id, [])),
                max_concurrency_slots=spec.max_concurrency_slots,
                fencing_epoch=self._fencing_epochs[spec.worker_id],
                registered_at=self._registration_times[spec.worker_id],
                last_heartbeat=self._last_heartbeats[spec.worker_id],
                capabilities=[c.name for c in spec.capabilities],
            )

    def list_snapshots(self) -> List[WorkerSnapshot]:
        with self._lock:
            return [self.get_snapshot(w_id) for w_id in self._workers if self._states[w_id] != WorkerState.DEREGISTERED]

    def list_available_workers(self, required_capabilities: Sequence[str] = ()) -> List[WorkerSnapshot]:
        with self._lock:
            snapshots = self.list_snapshots()
            available = []
            for snap in snapshots:
                if snap.is_available:
                    if required_capabilities:
                        if not all(cap in snap.capabilities for cap in required_capabilities):
                            continue
                    available.append(snap)
            return available
