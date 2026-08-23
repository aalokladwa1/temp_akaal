"""
akaalEngine.runtime.workers.heartbeat
======================================
Active WorkerHeartbeatTracker for health monitoring and stale worker eviction.
Mined from `akaal/distributed/worker/heartbeat.py`.
"""

import logging
from threading import RLock
import time
from typing import List, Optional

from akaalEngine.runtime.models.worker import WorkerHeartbeat, WorkerSnapshot, WorkerState
from akaalEngine.runtime.workers.registry import WorkerRegistry

logger = logging.getLogger("akaalEngine.runtime.workers.heartbeat")


class WorkerHeartbeatTracker:
    """
    WorkerHeartbeatTracker evaluating active worker heartbeats, detecting timeouts,
    and triggering stale-worker eviction.
    """

    def __init__(
        self,
        registry: WorkerRegistry,
        heartbeat_timeout_seconds: float = 15.0,
    ) -> None:
        self.registry = registry
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self._lock = RLock()

    def record_heartbeat(self, heartbeat: WorkerHeartbeat) -> WorkerSnapshot:
        with self._lock:
            self.registry.update_heartbeat(heartbeat.worker_id, heartbeat.timestamp)
            return self.registry.get_snapshot(heartbeat.worker_id)

    def detect_unhealthy_workers(self) -> List[WorkerSnapshot]:
        with self._lock:
            now = time.time()
            unhealthy: List[WorkerSnapshot] = []
            snapshots = self.registry.list_snapshots()

            for snap in snapshots:
                if snap.state in (WorkerState.DEREGISTERED, WorkerState.UNHEALTHY):
                    continue

                if (now - snap.last_heartbeat) > self.heartbeat_timeout_seconds:
                    logger.warning(
                        f"[WorkerHeartbeatTracker] Worker '{snap.worker_id}' heartbeat timeout "
                        f"({now - snap.last_heartbeat:.1f}s > {self.heartbeat_timeout_seconds}s). Marking UNHEALTHY."
                    )
                    updated = self.registry.update_state(snap.worker_id, WorkerState.UNHEALTHY)
                    unhealthy.append(updated)

            return unhealthy
