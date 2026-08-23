"""
akaalEngine.connection.sessions.lifecycle
=========================================
Session lease lifecycle management, lease validation, renewal, keepalive, and release.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from akaalEngine.connection.models.session import (
    InternalSessionHandle,
    SessionLease,
    SessionRequest,
)
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.sessions.reset import SessionResetManager

logger = logging.getLogger("akaalEngine.connection.sessions.lifecycle")


class SessionLifecycleManager:
    """
    Manages the lifecycle of active session leases and enforces lease scoping and reset.
    """

    def __init__(self) -> None:
        self._active_leases: Dict[str, SessionLease] = {}

    def checkout_lease(
        self,
        handle: InternalSessionHandle,
        request: SessionRequest,
        borrower_id: Optional[str] = None,
        ttl_seconds: float = 300.0,
    ) -> SessionLease:
        """
        Creates and returns a new SessionLease token wrapping the physical session handle.
        """
        borrower = borrower_id or request.borrower_id or "engine-worker"
        is_ro = request.is_effective_read_only()
        lease = SessionLease.create(
            session_handle=handle,
            purpose=request.purpose,
            isolation_level=request.isolation_level,
            is_read_only=is_ro,
            borrower_id=borrower,
            ttl_seconds=ttl_seconds,
        )
        self._active_leases[lease.lease_id] = lease
        handle.last_used_epoch = time.time()
        return lease

    def validate_lease(self, lease: SessionLease, strategy: Optional[BaseProviderStrategy] = None) -> bool:
        """
        Validates whether a lease is currently active and healthy.
        """
        if not lease.is_valid():
            return False
        if lease.lease_id not in self._active_leases:
            return False
        if strategy and lease._internal_handle and lease._internal_handle.physical_connection:
            try:
                return strategy.validate(lease._internal_handle.physical_connection)
            except Exception:
                return False
        return True

    def renew_lease(self, lease: SessionLease, extension_seconds: float = 300.0) -> SessionLease:
        """
        Extends the expiration deadline of an active session lease.
        """
        if not lease.is_valid():
            raise RuntimeError(f"Cannot renew invalid or closed lease '{lease.lease_id}'.")

        new_expires = (lease.expires_at_epoch or time.time()) + extension_seconds
        new_lease = SessionLease(
            lease_id=lease.lease_id,
            session_id=lease.session_id,
            purpose=lease.purpose,
            endpoint_fingerprint=lease.endpoint_fingerprint,
            provider_id=lease.provider_id,
            isolation_level=lease.isolation_level,
            is_read_only=lease.is_read_only,
            borrower_id=lease.borrower_id,
            created_at=lease.created_at,
            expires_at_epoch=new_expires,
            _internal_handle=lease._internal_handle,
        )
        self._active_leases[lease.lease_id] = new_lease
        return new_lease

    def release_lease(
        self,
        lease: SessionLease,
        strategy: BaseProviderStrategy,
    ) -> bool:
        """
        Releases a session lease and executes deterministic session reset.
        Returns True if session is clean and reusable, False if destroyed.
        """
        self._active_leases.pop(lease.lease_id, None)
        handle = lease._internal_handle
        if handle is None:
            return False

        return SessionResetManager.reset_and_clean_session(handle, strategy)

    def close_and_destroy_lease(
        self,
        lease: SessionLease,
        strategy: BaseProviderStrategy,
    ) -> None:
        """Permanently closes and destroys a physical session."""
        self._active_leases.pop(lease.lease_id, None)
        if lease._internal_handle:
            SessionResetManager.destroy_poisoned_session(lease._internal_handle, strategy)
