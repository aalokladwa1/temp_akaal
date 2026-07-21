"""
LeaseManager module for Distributed Runtime (Platform 2).
Manages task leases, renewals, expiration checks, and task reassignment triggering.
"""

from dataclasses import dataclass, field, replace
from threading import RLock
import logging

from akaal.distributed.domain.identifiers import LeaseId, WorkerId, TaskId
from akaal.distributed.domain.models import Lease, Task
from akaal.distributed.domain.errors import LeaseExpiredError
from akaal.distributed.repository.interfaces import LeaseRepository
from akaal.distributed.clock.clock import Clock, SystemClock
from akaal.distributed.events.events import EventPublisher, TaskLeased, LeaseExpired

logger = logging.getLogger("nexusforge.distributed.lease")


class LeaseManager:
    """
    LeaseManager managing task lease lifecycle and automatic eviction using Clock.
    """

    def __init__(
        self,
        repository: LeaseRepository,
        publisher: EventPublisher,
        default_ttl_seconds: float = 30.0,
        clock: Optional[Clock] = None,
    ) -> None:
        self._lock = RLock()
        self._repository = repository
        self._publisher = publisher
        self._default_ttl = default_ttl_seconds
        self._clock = clock or SystemClock()

    def acquire_lease(
        self,
        worker_id: WorkerId,
        task_id: TaskId,
        ttl_seconds: Optional[float] = None,
    ) -> Lease:
        """Acquire a new task lease."""
        with self._lock:
            existing = self._repository.get_lease_by_task(task_id)
            now = self._clock.now_timestamp()

            if existing and existing.expires_at > now:
                if str(existing.owner_worker_id) == str(worker_id):
                    return existing
                raise LeaseExpiredError(f"Task '{task_id}' is already leased by worker '{existing.owner_worker_id}'.")

            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            lease = Lease(
                lease_id=LeaseId.generate(),
                owner_worker_id=worker_id,
                task_id=task_id,
                created_at=now,
                expires_at=now + ttl,
                ttl_seconds=ttl,
            )
            self._repository.save_lease(lease)

            t_str = str(task_id)
            w_str = str(worker_id)
            l_str = str(lease.lease_id)

            self._publisher.publish(
                TaskLeased(
                    task_id=t_str,
                    worker_id=w_str,
                    lease_id=l_str,
                    expires_at=lease.expires_at,
                )
            )

            return lease

    def renew_lease(self, lease_id: LeaseId, worker_id: WorkerId) -> Lease:
        """Renew an existing lease."""
        with self._lock:
            lease = self._repository.get_lease(lease_id)
            if lease is None:
                raise LeaseExpiredError(f"Lease '{lease_id}' not found.")

            now = self._clock.now_timestamp()
            if lease.expires_at <= now:
                raise LeaseExpiredError(f"Lease '{lease_id}' expired at {lease.expires_at} (current time {now}).")

            if str(lease.owner_worker_id) != str(worker_id):
                raise LeaseExpiredError(f"Lease '{lease_id}' owner mismatch ({lease.owner_worker_id} != {worker_id}).")

            renewed = replace(lease, expires_at=now + lease.ttl_seconds)
            self._repository.update_lease(renewed)
            return renewed

    def revoke_lease(self, lease_id: LeaseId) -> None:
        """Revoke a lease."""
        with self._lock:
            self._repository.delete_lease(lease_id)

    def check_and_evict_expired_leases(self) -> List[Lease]:
        """Evict expired leases and publish LeaseExpired events."""
        with self._lock:
            now = self._clock.now_timestamp()
            active_leases = self._repository.list_active_leases()
            expired: List[Lease] = []

            for l in active_leases:
                if l.expires_at < now:
                    logger.warning(f"Lease '{l.lease_id}' for task '{l.task_id}' expired. Evicting lease.")
                    self._repository.delete_lease(l.lease_id)
                    expired.append(l)

                    l_str = str(l.lease_id)
                    t_str = str(l.task_id)
                    w_str = str(l.owner_worker_id)
                    self._publisher.publish(
                        LeaseExpired(
                            lease_id=l_str,
                            task_id=t_str,
                            worker_id=w_str,
                        )
                    )

            return expired
