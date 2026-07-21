"""
HeartbeatManager module for Distributed Runtime (Platform 2).
Manages worker heartbeats, lease timeouts, failure detection, and crash eviction.
"""

from dataclasses import dataclass, field, replace
from threading import RLock
import logging

from akaal.distributed.domain.identifiers import WorkerId
from akaal.distributed.domain.enums import WorkerStatus, WorkerHealth
from akaal.distributed.domain.models import Heartbeat, Worker
from akaal.distributed.domain.errors import DiscoveryError
from akaal.distributed.repository.interfaces import WorkerRepository
from akaal.distributed.clock.clock import Clock, SystemClock
from akaal.distributed.events.events import EventPublisher, WorkerHeartbeatEvent, WorkerUnavailable

logger = logging.getLogger("nexusforge.distributed.heartbeat")


class HeartbeatManager:
    """
    HeartbeatManager for monitoring worker health, detecting timeouts, and triggering recovery.
    """

    def __init__(
        self,
        repository: WorkerRepository,
        publisher: EventPublisher,
        heartbeat_timeout_seconds: float = 15.0,
        clock: Optional[Clock] = None,
    ) -> None:
        self._lock = RLock()
        self._repository = repository
        self._publisher = publisher
        self._heartbeat_timeout = heartbeat_timeout_seconds
        self._clock = clock or SystemClock()

    def record_heartbeat(self, heartbeat: Heartbeat) -> Worker:
        """Record worker heartbeat."""
        with self._lock:
            worker = self._repository.get_worker(heartbeat.worker_id)
            if worker is None:
                raise DiscoveryError(f"Worker '{heartbeat.worker_id}' not found.")

            now = self._clock.now_timestamp()
            updated = replace(
                worker,
                health=heartbeat.health,
                current_load=heartbeat.current_load,
                last_heartbeat=now,
            )
            self._repository.update_worker(updated)

            w_str = str(heartbeat.worker_id)
            self._publisher.publish(
                WorkerHeartbeatEvent(
                    worker_id=w_str,
                    status=updated.status.value,
                    health=updated.health.value,
                )
            )
            return updated

    def detect_unhealthy_workers(self) -> List[Worker]:
        """Inspect workers and mark those exceeding heartbeat_timeout as UNHEALTHY/OFFLINE."""
        with self._lock:
            now = self._clock.now_timestamp()
            workers = self._repository.list_workers()
            evicted: List[Worker] = []

            for w in workers:
                if w.status == WorkerStatus.REMOVED:
                    continue
                
                if (now - w.last_heartbeat) > self._heartbeat_timeout:
                    logger.warning(f"Worker '{w.worker_id}' heartbeat timeout (last seen {now - w.last_heartbeat:.1f}s ago). Marking UNHEALTHY.")
                    unhealthy = replace(w, health=WorkerHealth.UNHEALTHY, status=WorkerStatus.OFFLINE)
                    self._repository.update_worker(unhealthy)
                    evicted.append(unhealthy)

                    w_str = str(w.worker_id)
                    self._publisher.publish(
                        WorkerUnavailable(
                            worker_id=w_str,
                            reason="Heartbeat timeout",
                        )
                    )

            return evicted
