"""
WorkerRegistry module for Distributed Runtime (Platform 2).
Manages worker registration, status transitions, and capacity tracking.
"""

from dataclasses import dataclass, field, replace
from threading import RLock
from typing import Optional, List, Dict, Any
import logging

from akaal.distributed.domain.identifiers import WorkerId, NodeId
from akaal.distributed.domain.enums import WorkerStatus, WorkerHealth
from akaal.distributed.domain.models import Worker, WorkerCapability, ResourceSnapshot
from akaal.distributed.domain.errors import DiscoveryError
from akaal.distributed.repository.interfaces import WorkerRepository
from akaal.distributed.events.events import EventPublisher, WorkerRegistered, WorkerRemoved
from akaal.distributed.clock.clock import Clock, SystemClock

logger = logging.getLogger("nexusforge.distributed.registry")


class WorkerRegistry:
    """
    WorkerRegistry managing worker registrations, updates, and status lifecycle.
    """

    def __init__(
        self,
        repository: WorkerRepository,
        publisher: EventPublisher,
        clock: Optional[Clock] = None,
    ) -> None:
        self._lock = RLock()
        self._repository = repository
        self._publisher = publisher
        self._clock = clock or SystemClock()

    def register_worker(
        self,
        node_id: NodeId,
        capabilities: Optional[List[WorkerCapability]] = None,
        labels: Optional[Dict[str, str]] = None,
        capacity: int = 10,
        worker_id: Optional[WorkerId] = None,
        resources: Optional[ResourceSnapshot] = None,
    ) -> Worker:
        """Register a new worker."""
        with self._lock:
            w_id = worker_id or WorkerId.generate()
            now = self._clock.now_timestamp()

            worker = Worker(
                worker_id=w_id,
                node_id=node_id,
                status=WorkerStatus.REGISTERED,
                health=WorkerHealth.HEALTHY,
                labels=labels or {},
                capabilities=capabilities or [],
                capacity=capacity,
                current_load=0,
                resources=resources or ResourceSnapshot(),
                registration_timestamp=now,
                last_heartbeat=now,
            )
            self._repository.save_worker(worker)

            # Update to AVAILABLE
            available_worker = replace(worker, status=WorkerStatus.AVAILABLE)
            self._repository.update_worker(available_worker)

            w_str = str(w_id)
            n_str = str(node_id)
            cap_names = [c.name for c in available_worker.capabilities]

            self._publisher.publish(
                WorkerRegistered(
                    worker_id=w_str,
                    node_id=n_str,
                    capabilities=cap_names,
                )
            )

            logger.info(f"Worker '{w_str}' registered on node '{n_str}' with status AVAILABLE.")
            return available_worker

    def update_status(self, worker_id: WorkerId, new_status: WorkerStatus) -> Worker:
        """Update worker lifecycle status."""
        with self._lock:
            worker = self._repository.get_worker(worker_id)
            if worker is None:
                raise DiscoveryError(f"Worker '{worker_id}' not found.")
            updated = replace(worker, status=new_status)
            self._repository.update_worker(updated)
            return updated

    def deregister_worker(self, worker_id: WorkerId, reason: str = "voluntary") -> None:
        """Deregister a worker."""
        with self._lock:
            worker = self._repository.get_worker(worker_id)
            if worker:
                removed_worker = replace(worker, status=WorkerStatus.REMOVED)
                self._repository.update_worker(removed_worker)
                self._repository.delete_worker(worker_id)

                w_str = str(worker_id)
                self._publisher.publish(
                    WorkerRemoved(
                        worker_id=w_str,
                        reason=reason,
                    )
                )
                logger.info(f"Worker '{w_str}' deregistered ({reason}).")
