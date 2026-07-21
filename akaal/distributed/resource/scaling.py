"""
WorkerScalingManager module for Distributed Runtime (Platform 2).
Handles dynamic worker scale-up, scale-down, worker draining, graceful shutdown, and cluster rebalancing.
"""

from typing import List, Optional
from threading import RLock
import logging

from akaal.distributed.domain.identifiers import WorkerId, NodeId
from akaal.distributed.domain.enums import WorkerStatus
from akaal.distributed.domain.models import Worker
from akaal.distributed.worker.registry import WorkerRegistry
from akaal.distributed.events.events import EventPublisher, WorkerScaled

logger = logging.getLogger("nexusforge.distributed.scaling")


class WorkerScalingManager:
    """
    WorkerScalingManager managing worker pool sizing and draining.
    """

    def __init__(self, registry: WorkerRegistry, publisher: EventPublisher) -> None:
        self._lock = RLock()
        self._registry = registry
        self._publisher = publisher

    def scale_up(self, node_id: NodeId, count: int = 1) -> List[Worker]:
        """Scale up worker count on node_id."""
        with self._lock:
            new_workers: List[Worker] = []
            for _ in range(count):
                w = self._registry.register_worker(node_id=node_id)
                new_workers.append(w)

            self._publisher.publish(WorkerScaled(direction="SCALE_UP", worker_count=len(new_workers)))
            logger.info(f"Scaled UP cluster by {len(new_workers)} workers on node '{node_id}'.")
            return new_workers

    def drain_worker(self, worker_id: WorkerId) -> Worker:
        """Mark worker status as DRAINING to prevent new task assignments."""
        with self._lock:
            updated = self._registry.update_status(worker_id, WorkerStatus.DRAINING)
            logger.info(f"Worker '{worker_id}' status set to DRAINING.")
            return updated

    def scale_down(self, worker_id: WorkerId) -> None:
        """Deregister and scale down worker."""
        with self._lock:
            self._registry.deregister_worker(worker_id, reason="scaled_down")
            self._publisher.publish(WorkerScaled(direction="SCALE_DOWN", worker_count=1))
            logger.info(f"Scaled DOWN cluster by removing worker '{worker_id}'.")
