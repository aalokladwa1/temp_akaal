"""
akaalEngine.discovery.core.coordinator
======================================
Discovery session leasing and strategy resolution coordinator.
Strictly interfaces with frozen Connection Authority (#1) and Extensions Authority (#2).
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from akaalEngine.connection.api.authority import ConnectionAuthority, default_connection_authority
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.session import SessionLease, SessionPurpose, SessionRequest
from akaalEngine.discovery.errors.exceptions import EndpointUnreachableDiscoveryError, UnsupportedDiscoveryFeatureError
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy
from akaalEngine.extensions.authority import ExtensionsAuthority, default_extensions_authority
from akaalEngine.extensions.models.identity import AuthorityId, ProviderId
from akaalEngine.extensions.resolution.handles import ResolvedStrategyHandle

logger = logging.getLogger("akaalEngine.discovery.core.coordinator")


class DiscoverySessionCoordinator:
    """
    Coordinates leased read-only session handle acquisition from Connection Authority
    and strategy resolution from Extensions Authority with guaranteed deterministic cleanup.
    """

    def __init__(
        self,
        connection_authority: Optional[ConnectionAuthority] = None,
        extensions_authority: Optional[ExtensionsAuthority] = None,
    ) -> None:
        self._conn_auth = connection_authority or default_connection_authority
        self._ext_auth = extensions_authority or default_extensions_authority

    def acquire_discovery_session(
        self,
        spec: EndpointSpec,
        timeout_seconds: float = 30.0,
    ) -> SessionLease:
        """
        Acquires a leased session strictly for discovery purpose with read-only enforcement.
        """
        request = SessionRequest(
            purpose=SessionPurpose.DISCOVERY,
            endpoint_spec=spec,
            read_only=True,
        )
        try:
            return self._conn_auth.acquire_session_lease(
                request=request,
                borrower_id="DiscoveryAuthority",
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            raise EndpointUnreachableDiscoveryError(
                message=f"Failed to acquire discovery session lease for endpoint '{spec.provider_id}': {exc}",
                provider_id=spec.provider_id,
            ) from exc

    def release_discovery_session(self, lease: SessionLease, is_timed_out: bool = False) -> bool:
        """Releases a leased discovery session back to the Connection pool manager, discarding if timed out or poisoned."""
        if lease is None:
            return False
        if is_timed_out:
            return self.invalidate_discovery_session(lease)
        try:
            return self._conn_auth.release_session_lease(lease)
        except Exception as exc:
            logger.warning(f"[DiscoverySessionCoordinator] Error releasing session lease: {exc}")
            return False

    def invalidate_discovery_session(self, lease: SessionLease) -> bool:
        """Destroys, quarantines, and invalidates a timed-out or poisoned discovery session."""
        if lease is None:
            return False
        try:
            if getattr(lease, "_internal_handle", None) is not None:
                handle = lease._internal_handle
                raw_conn = getattr(handle, "physical_connection", None)
                if raw_conn is not None:
                    try:
                        if hasattr(raw_conn, "cancel"):
                            raw_conn.cancel()
                        if hasattr(raw_conn, "interrupt"):
                            raw_conn.interrupt()
                        if hasattr(raw_conn, "close"):
                            raw_conn.close()
                    except Exception:
                        pass
                handle.is_poisoned = True
                handle.is_closed = True
            self._conn_auth.invalidate_session(lease)
            self._conn_auth.release_session_lease(lease)
            return True
        except Exception as exc:
            logger.warning(f"[DiscoverySessionCoordinator] Error invalidating session lease: {exc}")
            return False

    def resolve_discovery_strategy(
        self,
        provider_id: str,
    ) -> Tuple[BaseDiscoveryStrategy, Optional[ResolvedStrategyHandle]]:
        """
        Resolves the concrete DiscoveryStrategy for a provider via Extensions Authority.
        """
        prov_id = ProviderId(provider_id)
        auth_id = AuthorityId("discovery")
        try:
            handle = self._ext_auth.resolve_strategy(
                provider_id=prov_id,
                authority_id=auth_id,
            )
            strategy_instance = handle.strategy_instance
            if callable(strategy_instance) and not isinstance(strategy_instance, BaseDiscoveryStrategy):
                strategy_instance = strategy_instance()
            if not isinstance(strategy_instance, BaseDiscoveryStrategy):
                raise UnsupportedDiscoveryFeatureError(
                    f"Resolved strategy for provider '{provider_id}' does not implement BaseDiscoveryStrategy.",
                    provider_id=provider_id,
                )
            return strategy_instance, handle
        except Exception as exc:
            raise UnsupportedDiscoveryFeatureError(
                f"Failed to resolve discovery strategy for provider '{provider_id}' via Extensions: {exc}",
                provider_id=provider_id,
            ) from exc

    def release_strategy_handle(self, handle: Optional[ResolvedStrategyHandle]) -> None:
        """Releases active strategy handle lease if present."""
        if handle is not None:
            try:
                self._ext_auth.release_strategy_handle(handle)
            except Exception as exc:
                logger.warning(f"[DiscoverySessionCoordinator] Error releasing strategy handle: {exc}")
