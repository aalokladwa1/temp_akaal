"""
akaalEngine.connection.pooling.pool
===================================
Process-local, identity-safe, bounded connection pool with PID/fork protection,
strict session reset, leak detection, and pressure metrics.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from akaalEngine.connection.models.errors import (
    ConnectionFailure,
    FailureCategory,
    PoolExhaustionError,
)
from akaalEngine.connection.models.health import (
    ConnectionPressureSnapshot,
    PoolSnapshot,
)
from akaalEngine.connection.models.session import (
    InternalSessionHandle,
    SessionLease,
    SessionPurpose,
    SessionRequest,
)
from akaalEngine.connection.pooling.policy import PoolPolicy
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.sessions.factory import SessionFactory
from akaalEngine.connection.sessions.lifecycle import SessionLifecycleManager
from akaalEngine.connection.sessions.reset import SessionResetManager

logger = logging.getLogger("akaalEngine.connection.pooling.pool")


class ConnectionPool:
    """
    Process-local, identity-safe physical connection pool.
    Enforces PID check on checkout to guarantee zero socket leak across OS fork().
    """

    def __init__(
        self,
        pool_id: str,
        fingerprint: str,
        provider_id: str,
        purpose: SessionPurpose,
        strategy: BaseProviderStrategy,
        factory: SessionFactory,
        policy: Optional[PoolPolicy] = None,
    ) -> None:
        self.pool_id = pool_id
        self.fingerprint = fingerprint
        self.provider_id = provider_id
        self.purpose = purpose
        self.strategy = strategy
        self.factory = factory
        self.policy = policy or PoolPolicy.default_for_role(purpose)

        self.created_pid = os.getpid()
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)

        # list of (handle, idle_since_epoch, validated_since_epoch)
        self._idle_handles: List[Tuple[InternalSessionHandle, float, float]] = []
        # session_id -> (handle, checkout_time_epoch, borrower_id)
        self._active_handles: Dict[str, Tuple[InternalSessionHandle, float, str]] = {}
        # session_id -> handle (all allocated in this pool)
        self._all_handles: Dict[str, InternalSessionHandle] = {}

        self.lifecycle_manager = SessionLifecycleManager()
        self._checkout_count = 0
        self._eviction_count = 0
        self._leaks_detected = 0
        self._created_at = datetime.now(timezone.utc).isoformat()
        self._last_pruned_at: Optional[str] = None
        self._pending_waiters = 0
        self._checkout_wait_times: List[float] = []

    def _check_fork_safety(self) -> None:
        """
        Guarantees child processes after fork() do not share parent socket file descriptors.
        """
        current_pid = os.getpid()
        if current_pid != self.created_pid:
            logger.warning(
                f"[ConnectionPool] Fork detected (parent PID {self.created_pid} != current PID {current_pid}). Discarding all sockets in pool '{self.pool_id}'."
            )
            # Reset handles without calling network close on parent sockets
            self._idle_handles.clear()
            self._active_handles.clear()
            self._all_handles.clear()
            self.created_pid = current_pid

    def acquire(
        self,
        request: SessionRequest,
        borrower_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> SessionLease:
        """
        Acquires a clean physical session lease from the pool, creating a new connection if under max_size.
        """
        timeout = timeout_seconds if timeout_seconds is not None else self.policy.acquisition_timeout_seconds
        deadline = time.time() + timeout
        t0 = time.perf_counter()

        with self._lock:
            self._check_fork_safety()
            self.prune_idle_and_expired()

            while True:
                # 1. Try to pop an idle valid connection
                while self._idle_handles:
                    handle, idle_since, val_since = self._idle_handles.pop()
                    now = time.time()

                    # Check max lifetime
                    if (now - handle.created_at_epoch) > self.policy.max_lifetime_seconds:
                        self._evict_handle(handle)
                        continue

                    # Validate if requested or interval passed
                    needs_val = self.policy.validate_on_checkout or (
                        (now - val_since) > self.policy.validation_interval_seconds
                    )
                    if needs_val:
                        if not self.strategy.validate(handle.physical_connection):
                            logger.info(f"[ConnectionPool] Connection validation failed for '{handle.session_id}'. Evicting.")
                            self._evict_handle(handle)
                            continue

                    # Successful checkout
                    self._active_handles[handle.session_id] = (handle, now, borrower_id or "worker")
                    self._checkout_count += 1
                    elapsed_wait_ms = (time.perf_counter() - t0) * 1000.0
                    self._record_wait_time(elapsed_wait_ms)

                    return self.lifecycle_manager.checkout_lease(
                        handle=handle,
                        request=request,
                        borrower_id=borrower_id,
                        ttl_seconds=300.0,
                    )

                # 2. If no idle connection, create a new one if below max_size
                if len(self._all_handles) < self.policy.max_size:
                    try:
                        handle, route = self.factory.create_physical_session(request)
                        now = time.time()
                        self._all_handles[handle.session_id] = handle
                        self._active_handles[handle.session_id] = (handle, now, borrower_id or "worker")
                        self._checkout_count += 1
                        elapsed_wait_ms = (time.perf_counter() - t0) * 1000.0
                        self._record_wait_time(elapsed_wait_ms)

                        return self.lifecycle_manager.checkout_lease(
                            handle=handle,
                            request=request,
                            borrower_id=borrower_id,
                            ttl_seconds=300.0,
                        )
                    except Exception as exc:
                        logger.error(f"[ConnectionPool] Error creating connection in pool '{self.pool_id}': {exc}")
                        raise

                # 3. Pool is saturated: wait on condition variable until connection released or deadline expires
                remaining = deadline - time.time()
                if remaining <= 0 or self._pending_waiters >= self.policy.max_waiters:
                    msg = f"Connection pool capacity exhausted for pool '{self.pool_id}' (max_size={self.policy.max_size}, active={len(self._active_handles)}, waiters={self._pending_waiters})."
                    failure = ConnectionFailure(
                        error_code="POOL_CAPACITY_EXHAUSTED",
                        category=FailureCategory.POOL_EXHAUSTION,
                        message=msg,
                        retryable=True,
                        provider_id=self.provider_id,
                        endpoint_fingerprint=self.fingerprint,
                        remediation="Increase pool max_size, increase timeout, or reduce borrower concurrency.",
                    )
                    raise PoolExhaustionError(failure)

                self._pending_waiters += 1
                try:
                    self._cond.wait(timeout=remaining)
                finally:
                    self._pending_waiters -= 1

    def release(self, lease: SessionLease) -> bool:
        """
        Releases a session lease, resets the connection, and returns it to idle queue or destroys it if dirty.
        """
        with self._lock:
            self._check_fork_safety()
            handle = lease._internal_handle
            if handle is None:
                return False

            self._active_handles.pop(handle.session_id, None)

            # Reset session
            is_clean = self.lifecycle_manager.release_lease(lease, self.strategy)
            if not is_clean or handle.is_poisoned or handle.is_closed:
                self._evict_handle(handle)
                self._cond.notify()
                return False

            now = time.time()
            self._idle_handles.append((handle, now, now))
            self._cond.notify()
            return True

    def _evict_handle(self, handle: InternalSessionHandle) -> None:
        """Internal helper to close and remove a connection from the pool."""
        self._all_handles.pop(handle.session_id, None)
        self._active_handles.pop(handle.session_id, None)
        SessionResetManager.destroy_poisoned_session(handle, self.strategy)
        self._eviction_count += 1

    def prune_idle_and_expired(self) -> None:
        """Prunes expired idle connections while respecting min_size."""
        with self._lock:
            now = time.time()
            self._last_pruned_at = datetime.now(timezone.utc).isoformat()
            retained_idle: list[tuple[InternalSessionHandle, float, float]] = []

            for handle, idle_since, val_since in self._idle_handles:
                is_idle_expired = (now - idle_since) > self.policy.idle_timeout_seconds
                is_lifetime_expired = (now - handle.created_at_epoch) > self.policy.max_lifetime_seconds

                if (is_idle_expired or is_lifetime_expired) and len(self._all_handles) > self.policy.min_size:
                    self._evict_handle(handle)
                else:
                    retained_idle.append((handle, idle_since, val_since))

            self._idle_handles = retained_idle

    def prewarm(self, count: Optional[int] = None) -> int:
        """Prewarms the pool up to the specified count or min_size."""
        target_count = count if count is not None else self.policy.min_size
        created = 0
        with self._lock:
            self._check_fork_safety()
            from akaalEngine.connection.models.endpoint import EndpointSpec
            spec = EndpointSpec(provider_id=self.provider_id)
            req = SessionRequest(purpose=self.purpose, endpoint_spec=spec)

            while len(self._all_handles) < target_count and len(self._all_handles) < self.policy.max_size:
                try:
                    handle, _ = self.factory.create_physical_session(req)
                    now = time.time()
                    self._all_handles[handle.session_id] = handle
                    self._idle_handles.append((handle, now, now))
                    created += 1
                except Exception as exc:
                    logger.warning(f"[ConnectionPool] Prewarm error in '{self.pool_id}': {exc}")
                    break
        return created

    def invalidate_all(self) -> None:
        """Invalidates and permanently destroys all idle and active connections in this pool."""
        with self._lock:
            logger.info(f"[ConnectionPool] Invalidate all requested for pool '{self.pool_id}'.")
            for handle, _, _ in self._idle_handles:
                SessionResetManager.destroy_poisoned_session(handle, self.strategy)
            self._idle_handles.clear()

            for sid, (handle, _, _) in list(self._active_handles.items()):
                handle.is_poisoned = True  # Caller will see lease invalidated on next use
                SessionResetManager.destroy_poisoned_session(handle, self.strategy)
            self._active_handles.clear()
            self._all_handles.clear()
            self._cond.notify_all()

    def detect_leaks(self, leak_threshold_seconds: float = 600.0) -> List[Dict[str, Any]]:
        """Detects unreleased active sessions checked out longer than threshold."""
        leaks = []
        with self._lock:
            now = time.time()
            for sid, (handle, checkout_time, borrower) in self._active_handles.items():
                duration = now - checkout_time
                if duration > leak_threshold_seconds:
                    leaks.append({
                        "session_id": sid,
                        "borrower_id": borrower,
                        "checkout_duration_seconds": round(duration, 2),
                        "purpose": handle.purpose.value,
                    })
                    self._leaks_detected += 1
        return leaks

    def _record_wait_time(self, wait_ms: float) -> None:
        self._checkout_wait_times.append(wait_ms)
        if len(self._checkout_wait_times) > 100:
            self._checkout_wait_times.pop(0)

    def get_snapshot(self) -> PoolSnapshot:
        with self._lock:
            return PoolSnapshot(
                pool_id=self.pool_id,
                endpoint_fingerprint=self.fingerprint,
                provider_id=self.provider_id,
                purpose=self.purpose.value,
                total_allocated=len(self._all_handles),
                active_count=len(self._active_handles),
                idle_count=len(self._idle_handles),
                min_size=self.policy.min_size,
                max_size=self.policy.max_size,
                checkout_count=self._checkout_count,
                eviction_count=self._eviction_count,
                leaks_detected=self._leaks_detected,
                created_at=self._created_at,
                last_pruned_at=self._last_pruned_at,
            )

    def get_pressure_snapshot(self) -> ConnectionPressureSnapshot:
        with self._lock:
            active = len(self._active_handles)
            idle = len(self._idle_handles)
            total = active + idle
            ratio = (active / total) if total > 0 else 0.0
            is_sat = (active >= self.policy.max_size) or (self._pending_waiters > 0)
            avg_wait = sum(self._checkout_wait_times) / len(self._checkout_wait_times) if self._checkout_wait_times else 0.0
            max_wait = max(self._checkout_wait_times) if self._checkout_wait_times else 0.0

            return ConnectionPressureSnapshot(
                endpoint_fingerprint=self.fingerprint,
                provider_id=self.provider_id,
                active_leases_count=active,
                idle_pool_count=idle,
                pending_waiters_count=self._pending_waiters,
                pool_utilization_ratio=ratio,
                is_saturated=is_sat,
                avg_checkout_wait_ms=avg_wait,
                max_checkout_wait_ms=max_wait,
                recommended_concurrency_ceiling=self.policy.max_size,
            )
