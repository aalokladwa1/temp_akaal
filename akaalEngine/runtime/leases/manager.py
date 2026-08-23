"""
akaalEngine.runtime.leases.manager
===================================
ExecutionLeaseManager managing active task execution leases and enforcing fencing epochs.
Physically integrates with Durability Authority #5 FencingTokenManager.
"""

from dataclasses import dataclass, field
import logging
from threading import RLock
import time
from typing import Any, Dict, Optional

from akaalEngine.runtime.models.errors import FencingRejectedError, LeaseExpiredError

logger = logging.getLogger("akaalEngine.runtime.leases")


@dataclass(frozen=True)
class ExecutionLease:
    """
    Active task execution lease descriptor.
    """
    lease_id: str
    task_id: str
    worker_id: str
    fencing_epoch: int
    attempt_id: str
    acquired_at: float
    expires_at: float
    durability_token: Optional[Any] = None

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "fencing_epoch": self.fencing_epoch,
            "attempt_id": self.attempt_id,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
            "is_expired": self.is_expired,
        }


class ExecutionLeaseManager:
    """
    ExecutionLeaseManager managing task execution leases, lease renewals,
    expiration tracking, and fencing epoch validation.
    """

    def __init__(
        self,
        durability_fencing_manager: Optional[Any] = None,
        default_ttl_seconds: float = 30.0,
    ) -> None:
        self.durability_fencing_manager = durability_fencing_manager
        self.default_ttl_seconds = default_ttl_seconds
        self._leases: Dict[str, ExecutionLease] = {}
        self._task_leases: Dict[str, str] = {}
        self._resource_epochs: Dict[str, int] = {}
        self._attempt_counts: Dict[str, int] = {}
        self._lock = RLock()

    def acquire_lease(
        self,
        task_id: str,
        worker_id: str,
        ttl_seconds: Optional[float] = None,
        fencing_epoch: Optional[int] = None,
    ) -> ExecutionLease:
        with self._lock:
            now = time.time()
            ttl = ttl_seconds or self.default_ttl_seconds

            # Fencing Epoch check
            curr_epoch = self._resource_epochs.get(task_id, 0)
            epoch = fencing_epoch if fencing_epoch is not None else (curr_epoch + 1)
            if epoch < curr_epoch:
                raise FencingRejectedError(active_epoch=curr_epoch, attempted_epoch=epoch, entity_id=task_id)

            self._resource_epochs[task_id] = epoch
            attempt_num = self._attempt_counts.get(task_id, 0) + 1
            self._attempt_counts[task_id] = attempt_num
            attempt_id = f"att-{task_id}-{worker_id}-{epoch}-{attempt_num}"

            # Physical Durability #5 Integration
            durability_token = None
            if self.durability_fencing_manager:
                try:
                    durability_token = self.durability_fencing_manager.issue_token(resource_id=task_id, worker_id=worker_id)
                    epoch = durability_token.fencing_epoch
                    self._resource_epochs[task_id] = epoch
                except Exception as exc:
                    logger.warning(f"[ExecutionLeaseManager] Durability fencing token issue failed: {exc}")

            lease_id = f"lease-{task_id}-{worker_id}-{epoch}"
            lease = ExecutionLease(
                lease_id=lease_id,
                task_id=task_id,
                worker_id=worker_id,
                fencing_epoch=epoch,
                attempt_id=attempt_id,
                acquired_at=now,
                expires_at=now + ttl,
                durability_token=durability_token,
            )

            self._leases[lease_id] = lease
            self._task_leases[task_id] = lease_id
            logger.info(f"[ExecutionLeaseManager] Acquired lease '{lease_id}' for task '{task_id}' (attempt={attempt_id}).")
            return lease

    def renew_lease(self, lease_id: str, ttl_seconds: Optional[float] = None) -> ExecutionLease:
        with self._lock:
            lease = self._leases.get(lease_id)
            if not lease:
                raise LeaseExpiredError(lease_id)

            if lease.is_expired:
                self.release_lease(lease_id)
                raise LeaseExpiredError(lease_id)

            now = time.time()
            ttl = ttl_seconds or self.default_ttl_seconds
            renewed = ExecutionLease(
                lease_id=lease.lease_id,
                task_id=lease.task_id,
                worker_id=lease.worker_id,
                fencing_epoch=lease.fencing_epoch,
                attempt_id=lease.attempt_id,
                acquired_at=lease.acquired_at,
                expires_at=now + ttl,
                durability_token=lease.durability_token,
            )

            self._leases[lease_id] = renewed
            return renewed

    def validate_lease(self, lease_id: str, fencing_epoch: int) -> bool:
        with self._lock:
            lease = self._leases.get(lease_id)
            if not lease or lease.is_expired:
                return False

            curr_epoch = self._resource_epochs.get(lease.task_id, 0)
            if fencing_epoch < curr_epoch or lease.fencing_epoch < curr_epoch:
                return False

            # Durability check if available
            if self.durability_fencing_manager and lease.durability_token:
                try:
                    return self.durability_fencing_manager.validate_token(lease.durability_token)
                except Exception:
                    return False

            return True

    def release_lease(self, lease_id: str) -> None:
        with self._lock:
            lease = self._leases.pop(lease_id, None)
            if lease:
                self._task_leases.pop(lease.task_id, None)

    def get_lease_for_task(self, task_id: str) -> Optional[ExecutionLease]:
        with self._lock:
            lease_id = self._task_leases.get(task_id)
            if lease_id:
                lease = self._leases.get(lease_id)
                if lease and not lease.is_expired:
                    return lease
                elif lease and lease.is_expired:
                    self.release_lease(lease_id)
            return None
