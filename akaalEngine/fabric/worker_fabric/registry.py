"""
akaalEngine.fabric.worker_fabric.registry
=============================================
P7B.22 -- Elastic Worker Fabric registration/heartbeat/replacement seam. P7B.23's
self-healing fencing law is enforced HERE (registration-time), not bolted on separately,
because "a duplicate/stale worker cannot create duplicate authoritative execution" is
fundamentally a registration-identity problem, exactly like SiteRegistry's fencing.

CRITICAL LAW: registration/heartbeat is bookkeeping, never trust and never authorization.
A newly-registered worker is never automatically eligible for assignment merely by
existing here -- see module docstring in worker_fabric.models.

Fencing law (P7B.23, reusing the exact SiteRegistry/SiteAssignment discipline, never a
second scheme): `replace_worker` requires the REPLACEMENT worker's fencing_epoch to be
strictly greater than the epoch last recorded for that (tenant, site, worker slot) --
a stale worker attempting to (re)register with an epoch <= the last recorded epoch is
refused outright, closing exactly the "stale worker returns after replacement" and
"old worker returns after rolling upgrade" hostile scenarios.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from akaalEngine.fabric.worker_fabric.models import WorkerCapacity, WorkerNode, WorkerState, WorkerValidationError


class WorkerRegistrationError(WorkerValidationError):
    pass


class DuplicateWorkerIdentityError(WorkerRegistrationError):
    pass


class CrossTenantWorkerError(WorkerRegistrationError):
    pass


class StaleWorkerFencingError(WorkerRegistrationError):
    """A worker attempted to register/replace with a fencing_epoch that does not exceed
    the last recorded epoch for its slot -- refused outright, never silently accepted at
    a lower trust level."""


class UnknownWorkerError(KeyError):
    pass


_Key = Tuple[str, str]  # (tenant_id, worker_id)


class WorkerRegistry:
    """Thread-safe, tenant-scoped worker registration/heartbeat/replacement authority."""

    def __init__(self, durability_store: Optional[Any] = None) -> None:
        self._lock = threading.RLock()
        self._workers: Dict[_Key, WorkerNode] = {}
        # last recorded fencing epoch per (tenant, site_id) "worker slot" -- a slot
        # persists across worker replacement (old worker_id -> new worker_id), exactly
        # like SiteRegistry tracks the last epoch per site_id, not per assignment.
        self._last_epoch_by_slot: Dict[Tuple[str, str], int] = {}
        self._durability_store = durability_store

    @staticmethod
    def _key(tenant_id: str, worker_id: str) -> _Key:
        return (tenant_id, worker_id)

    def register(self, worker: WorkerNode) -> WorkerNode:
        """First-time registration for a NEW worker identity. Use `replace_worker` (not
        this method) when a worker is explicitly replacing a previous one at the same
        site -- calling `register` twice for the SAME worker_id is idempotent only if the
        (tenant, site) pair matches; a genuinely different worker attempting to reuse an
        existing worker_id is rejected."""
        with self._lock:
            key = self._key(worker.tenant_id, worker.worker_id)
            existing = self._workers.get(key)
            if existing is not None and (existing.site_id != worker.site_id):
                raise DuplicateWorkerIdentityError(
                    f"worker_id {worker.worker_id!r} is already registered against a "
                    f"different site {existing.site_id!r}; refusing to silently repoint."
                )
            slot = (worker.tenant_id, worker.site_id)
            last_epoch = self._last_epoch_by_slot.get(slot, 0)
            if worker.fencing_epoch <= last_epoch:
                raise StaleWorkerFencingError(
                    f"worker {worker.worker_id!r} fencing_epoch {worker.fencing_epoch} does "
                    f"not exceed last recorded epoch {last_epoch} for slot {slot!r}; refusing "
                    f"stale/replayed worker registration."
                )
            self._workers[key] = worker
            self._last_epoch_by_slot[slot] = worker.fencing_epoch
            if self._durability_store is not None:
                self._durability_store.save_worker(worker)
            return worker

    def _register_reconstructed(self, worker: WorkerNode) -> None:
        with self._lock:
            key = self._key(worker.tenant_id, worker.worker_id)
            self._workers[key] = worker
            slot = (worker.tenant_id, worker.site_id)
            self._last_epoch_by_slot[slot] = max(self._last_epoch_by_slot.get(slot, 0), worker.fencing_epoch)

    def replace_worker(self, old_worker_id: str, new_worker: WorkerNode) -> WorkerNode:
        """
        Explicit, self-healing/rolling-operation replacement (P7B.23): registers
        `new_worker` and marks the old worker REVOKED in the same atomic step, enforcing
        the same fencing-epoch monotonicity `register` does. A caller replacing a crashed
        worker must supply a strictly higher fencing_epoch than the slot's last recorded
        epoch -- this is what prevents a duplicate pod/process from creating duplicate
        authoritative execution: only one worker per (tenant, site) slot can ever hold
        the current-highest epoch at a time.
        """
        with self._lock:
            registered = self.register(new_worker)  # raises StaleWorkerFencingError if not strictly newer
            old_key = self._key(new_worker.tenant_id, old_worker_id)
            old = self._workers.get(old_key)
            if old is not None and old.worker_id != new_worker.worker_id:
                revoked = WorkerNode(
                    worker_id=old.worker_id, site_id=old.site_id, tenant_id=old.tenant_id,
                    runtime_version=old.runtime_version, capabilities=old.capabilities,
                    capability_provenance=old.capability_provenance, capacity=old.capacity,
                    state=WorkerState.REVOKED, fencing_epoch=old.fencing_epoch,
                    registered_at=old.registered_at, last_heartbeat_at=old.last_heartbeat_at,
                    labels=old.labels,
                )
                self._workers[old_key] = revoked
                if self._durability_store is not None:
                    self._durability_store.save_worker(revoked)
            return registered

    def heartbeat(
        self, worker_id: str, tenant_id: str, *, capacity: Optional[WorkerCapacity] = None,
        state: Optional[WorkerState] = None, now: Optional[datetime] = None,
    ) -> WorkerNode:
        with self._lock:
            existing = self._get_internal(worker_id, tenant_id)
            if existing.state in (WorkerState.REVOKED,):
                raise WorkerRegistrationError(
                    f"worker {worker_id!r} is REVOKED; a revoked worker can never heartbeat "
                    f"back into active state -- this closes the 'stale worker returns' path."
                )
            updated = WorkerNode(
                worker_id=existing.worker_id, site_id=existing.site_id, tenant_id=existing.tenant_id,
                runtime_version=existing.runtime_version, capabilities=existing.capabilities,
                capability_provenance=existing.capability_provenance,
                capacity=capacity if capacity is not None else existing.capacity,
                state=state if state is not None else existing.state,
                fencing_epoch=existing.fencing_epoch, registered_at=existing.registered_at,
                last_heartbeat_at=(now or datetime.now(timezone.utc)).isoformat(),
                labels=existing.labels,
            )
            key = self._key(tenant_id, worker_id)
            self._workers[key] = updated
            if self._durability_store is not None:
                self._durability_store.save_worker(updated)
            return updated

    def is_stale(self, worker_id: str, tenant_id: str, max_heartbeat_age_seconds: float, now: Optional[datetime] = None) -> bool:
        worker = self.get(worker_id, tenant_id)
        return worker.seconds_since_heartbeat(now) > max_heartbeat_age_seconds

    def request_drain(self, worker_id: str, tenant_id: str) -> WorkerNode:
        """DRAIN -> stop new assignments; never immediately terminates. Terminating
        infrastructure while active work exists is a separate, later step this registry
        does not itself perform (it has no notion of 'active work' -- that lives in the
        canonical runtime, not here)."""
        return self._transition(worker_id, tenant_id, WorkerState.DRAINING, allow_from=(WorkerState.IDLE, WorkerState.BUSY))

    def mark_unhealthy(self, worker_id: str, tenant_id: str) -> WorkerNode:
        return self._transition(worker_id, tenant_id, WorkerState.UNHEALTHY, allow_from=None)

    def revoke(self, worker_id: str, tenant_id: str) -> WorkerNode:
        return self._transition(worker_id, tenant_id, WorkerState.REVOKED, allow_from=None)

    def mark_stale(self, worker_id: str, tenant_id: str) -> WorkerNode:
        return self._transition(worker_id, tenant_id, WorkerState.STALE, allow_from=None)

    def _transition(self, worker_id: str, tenant_id: str, new_state: WorkerState, *, allow_from) -> WorkerNode:
        with self._lock:
            existing = self._get_internal(worker_id, tenant_id)
            if existing.state == WorkerState.REVOKED:
                raise WorkerRegistrationError(f"worker {worker_id!r} is REVOKED; state is terminal.")
            if allow_from is not None and existing.state not in allow_from:
                raise WorkerRegistrationError(
                    f"worker {worker_id!r} cannot transition from {existing.state.value} to "
                    f"{new_state.value} via this path."
                )
            updated = WorkerNode(
                worker_id=existing.worker_id, site_id=existing.site_id, tenant_id=existing.tenant_id,
                runtime_version=existing.runtime_version, capabilities=existing.capabilities,
                capability_provenance=existing.capability_provenance, capacity=existing.capacity,
                state=new_state, fencing_epoch=existing.fencing_epoch, registered_at=existing.registered_at,
                last_heartbeat_at=existing.last_heartbeat_at, labels=existing.labels,
            )
            key = self._key(tenant_id, worker_id)
            self._workers[key] = updated
            if self._durability_store is not None:
                self._durability_store.save_worker(updated)
            return updated

    def _get_internal(self, worker_id: str, tenant_id: str) -> WorkerNode:
        worker = self._workers.get(self._key(tenant_id, worker_id))
        if worker is None:
            raise UnknownWorkerError(f"Unknown worker_id: {worker_id!r}")
        if worker.tenant_id != tenant_id:
            raise CrossTenantWorkerError(f"worker_id {worker_id!r} belongs to a different tenant; refusing cross-tenant access.")
        return worker

    def get(self, worker_id: str, tenant_id: str) -> WorkerNode:
        with self._lock:
            return self._get_internal(worker_id, tenant_id)

    def list_workers_for_site(self, site_id: str, tenant_id: str) -> Tuple[WorkerNode, ...]:
        with self._lock:
            return tuple(w for w in self._workers.values() if w.tenant_id == tenant_id and w.site_id == site_id)

    def list_workers_for_tenant(self, tenant_id: str) -> Tuple[WorkerNode, ...]:
        with self._lock:
            return tuple(w for w in self._workers.values() if w.tenant_id == tenant_id)


default_worker_registry = WorkerRegistry()
