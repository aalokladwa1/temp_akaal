"""
akaalEngine.connection.pooling.manager
======================================
Process-local top-level PoolManager coordinating isolated budget pools,
asymmetric source/target limits, and invalidation routing.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Dict, List, Optional, Tuple

from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog, default_provider_catalog
from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.health import (
    ConnectionPressureSnapshot,
    PoolSnapshot,
)
from akaalEngine.connection.models.session import (
    SessionLease,
    SessionPurpose,
    SessionRequest,
)
from akaalEngine.connection.pooling.invalidation import (
    PoolInvalidationCoordinator,
    default_invalidation_coordinator,
)
from akaalEngine.connection.pooling.policy import PoolPolicy
from akaalEngine.connection.pooling.pool import ConnectionPool
from akaalEngine.connection.sessions.factory import SessionFactory, default_session_factory

logger = logging.getLogger("akaalEngine.connection.pooling.manager")


class PoolManager:
    """
    Top-level connection pool manager for akaalEngine.
    Partitions pools by (fingerprint, purpose, pid) to ensure complete isolation between workloads.
    """

    def __init__(
        self,
        catalog: Optional[ProviderCatalog] = None,
        factory: Optional[SessionFactory] = None,
        invalidation_coordinator: Optional[PoolInvalidationCoordinator] = None,
    ) -> None:
        self.catalog = catalog or default_provider_catalog
        self.factory = factory or default_session_factory
        self.invalidation_coordinator = invalidation_coordinator or default_invalidation_coordinator
        self._lock = threading.RLock()
        # (fingerprint, purpose, pid) -> ConnectionPool
        self._pools: Dict[Tuple[str, SessionPurpose, int], ConnectionPool] = {}

        # Register listener for automated invalidation
        self.invalidation_coordinator.register_invalidation_listener(self._handle_invalidation_signal)

    def _handle_invalidation_signal(self, fingerprint: Optional[str], reason: Optional[str]) -> None:
        """Invoked when invalidation coordinator broadcasts an invalidation signal."""
        with self._lock:
            current_pid = os.getpid()
            if fingerprint:
                for key, pool in list(self._pools.items()):
                    if key[0] == fingerprint:
                        pool.invalidate_all()
                        self._pools.pop(key, None)
            else:
                for pool in self._pools.values():
                    pool.invalidate_all()
                self._pools.clear()

    def get_or_create_pool(
        self,
        request: SessionRequest,
        policy: Optional[PoolPolicy] = None,
    ) -> ConnectionPool:
        """
        Retrieves or allocates a dedicated process-local pool for an endpoint and session purpose.
        """
        spec = request.endpoint_spec
        cat_gen = self.catalog.get_catalog_generation() if hasattr(self.catalog, "get_catalog_generation") else 1
        fp = compute_endpoint_fingerprint(spec, catalog_generation=cat_gen).fingerprint_sha256
        purpose = request.purpose
        current_pid = os.getpid()
        key = (fp, purpose, current_pid)

        with self._lock:
            if key in self._pools:
                return self._pools[key]

            strategy = self.catalog.get_strategy(spec.provider_id)
            pool_id = f"pool-{spec.provider_id}-{purpose.value.lower()}-{fp[:8]}-{current_pid}"
            effective_policy = policy or PoolPolicy.default_for_role(spec.role)

            pool = ConnectionPool(
                pool_id=pool_id,
                fingerprint=fp,
                provider_id=spec.provider_id,
                purpose=purpose,
                strategy=strategy,
                factory=self.factory,
                policy=effective_policy,
            )
            self._pools[key] = pool
            logger.info(f"[PoolManager] Allocated new pool '{pool_id}' (role={spec.role.value}, max_size={effective_policy.max_size}).")
            return pool

    def acquire_session(
        self,
        request: SessionRequest,
        borrower_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        policy: Optional[PoolPolicy] = None,
    ) -> SessionLease:
        """
        Acquires a session lease from the appropriate pool.
        """
        pool = self.get_or_create_pool(request, policy)
        return pool.acquire(request, borrower_id=borrower_id, timeout_seconds=timeout_seconds)

    def release_session(self, lease: SessionLease) -> bool:
        """
        Releases a session lease back to its owning pool.
        """
        fp = lease.endpoint_fingerprint
        purpose = lease.purpose
        current_pid = os.getpid()
        key = (fp, purpose, current_pid)

        with self._lock:
            pool = self._pools.get(key)
            if pool:
                return pool.release(lease)
            else:
                # If pool was already evicted/invalidated, destroy physical session
                strategy = self.catalog.get_strategy(lease.provider_id)
                pool_dummy = ConnectionPool(
                    pool_id="orphan",
                    fingerprint=fp,
                    provider_id=lease.provider_id,
                    purpose=purpose,
                    strategy=strategy,
                    factory=self.factory,
                )
                pool_dummy.lifecycle_manager.close_and_destroy_lease(lease, strategy)
                return False

    def invalidate_endpoint(self, fingerprint: str) -> int:
        """Invalidates all pools matching the given endpoint fingerprint."""
        with self._lock:
            count = 0
            for key, pool in list(self._pools.items()):
                if key[0] == fingerprint:
                    pool.invalidate_all()
                    self._pools.pop(key, None)
                    count += 1
            return count

    def invalidate_all(self) -> int:
        """Invalidates all pools across all endpoints."""
        with self._lock:
            count = len(self._pools)
            for pool in self._pools.values():
                pool.invalidate_all()
            self._pools.clear()
            return count

    def get_pool_snapshot(
        self,
        fingerprint: str,
        purpose: Optional[SessionPurpose] = None,
    ) -> Optional[PoolSnapshot]:
        with self._lock:
            current_pid = os.getpid()
            for (fp, purp, pid), pool in self._pools.items():
                if fp == fingerprint and pid == current_pid:
                    if purpose is None or purp == purpose:
                        return pool.get_snapshot()
            return None

    def get_all_pool_snapshots(self) -> List[PoolSnapshot]:
        with self._lock:
            return [pool.get_snapshot() for pool in self._pools.values()]

    def get_pressure_snapshot(self, fingerprint: str) -> Optional[ConnectionPressureSnapshot]:
        with self._lock:
            current_pid = os.getpid()
            for (fp, _, pid), pool in self._pools.items():
                if fp == fingerprint and pid == current_pid:
                    return pool.get_pressure_snapshot()
            return None

    def detect_all_leaks(self, leak_threshold_seconds: float = 600.0) -> List[dict[str, Any]]:
        with self._lock:
            all_leaks = []
            for pool in self._pools.values():
                all_leaks.extend(pool.detect_leaks(leak_threshold_seconds))
            return all_leaks


# Global default pool manager
default_pool_manager = PoolManager()
