"""
akaalEngine.connection.api.authority
====================================
Single Canonical Façade: ConnectionAuthority.
Exposes public sanitized diagnostic operations and internal Engine session lease acquisition.
Guarantees zero leakage of native handles, secrets, mutable pools, or unredacted exceptions.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, List, Optional, Sequence, Union

from akaalEngine.connection.catalog.capability_resolver import (
    CapabilityResolver,
    default_capability_resolver,
)
from akaalEngine.connection.catalog.provider_catalog import (
    ProviderCatalog,
    default_provider_catalog,
)
from akaalEngine.connection.identity.attestation import IdentityAttestor
from akaalEngine.connection.identity.drift import DriftDetector
from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.capability import (
    CapabilitySupportStatus,
    PermissionSnapshot,
    ProbedCapabilitySnapshot,
    StaticCapabilityManifest,
)
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.models.health import (
    ConnectionHealthSnapshot,
    ConnectionPressureSnapshot,
    ConnectionTestResult,
    PoolSnapshot,
)
from akaalEngine.connection.models.identity import (
    DriftReport,
    EndpointBindingFingerprint,
    PhysicalEndpointIdentity,
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
from akaalEngine.connection.pooling.manager import PoolManager, default_pool_manager
from akaalEngine.connection.pooling.policy import PoolPolicy
from akaalEngine.connection.probes.capabilities import CapabilityProbe
from akaalEngine.connection.probes.connectivity import ConnectivityProbe
from akaalEngine.connection.probes.health import HealthProbe
from akaalEngine.connection.probes.permissions import PermissionProbe
from akaalEngine.connection.probes.pressure import PressureProbe
from akaalEngine.connection.routing.dns import EnterpriseDNSResolver, default_dns_resolver
from akaalEngine.connection.routing.resolver import RouteResolver, default_route_resolver
from akaalEngine.connection.security.redaction import redact_mapping, redact_text
from akaalEngine.connection.security.secret_consumer import SecretConsumer, default_secret_consumer
from akaalEngine.connection.sessions.factory import SessionFactory, default_session_factory
from akaalEngine.connection.sessions.lifecycle import SessionLifecycleManager

logger = logging.getLogger("akaalEngine.connection.authority")


class ConnectionAuthority:
    """
    The Single Canonical Façade for Authority #1: Connection.
    Consumed by future EngineGateway, Discovery, Schema, Transport, Change Capture, and Validation.
    """

    _INSTANCE: Optional["ConnectionAuthority"] = None
    _LOCK = threading.RLock()

    def __init__(
        self,
        catalog: Optional[ProviderCatalog] = None,
        capability_resolver: Optional[CapabilityResolver] = None,
        pool_manager: Optional[PoolManager] = None,
        route_resolver: Optional[RouteResolver] = None,
        dns_resolver: Optional[EnterpriseDNSResolver] = None,
        secret_consumer: Optional[SecretConsumer] = None,
        session_factory: Optional[SessionFactory] = None,
        invalidation_coordinator: Optional[PoolInvalidationCoordinator] = None,
    ) -> None:
        self.catalog = catalog or default_provider_catalog
        self.capability_resolver = capability_resolver or default_capability_resolver
        self.secret_consumer = secret_consumer or default_secret_consumer
        self.dns_resolver = dns_resolver or default_dns_resolver
        self.route_resolver = route_resolver or default_route_resolver
        self.session_factory = session_factory or default_session_factory
        self.invalidation_coordinator = invalidation_coordinator or default_invalidation_coordinator
        self.pool_manager = pool_manager or default_pool_manager
        self.lifecycle_manager = SessionLifecycleManager()

        # Probes
        self._connectivity_probe = ConnectivityProbe(
            self.catalog, self.dns_resolver, self.route_resolver, self.secret_consumer
        )
        self._permission_probe = PermissionProbe(self.catalog, self.session_factory)
        self._capability_probe = CapabilityProbe(self.catalog, self.session_factory)
        self._health_probe = HealthProbe(self.catalog, self.session_factory)
        self._pressure_probe = PressureProbe(self.pool_manager)

    @classmethod
    def get_instance(cls) -> "ConnectionAuthority":
        """Singleton accessor with thread-safe double-checked locking."""
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
        return cls._INSTANCE

    # =========================================================================
    # 1. PUBLIC / SANITIZED CONNECTOR & PROVIDER CATALOG OPERATIONS
    # =========================================================================

    def list_providers(self) -> List[str]:
        """Returns a sorted list of registered provider IDs."""
        return self.catalog.list_providers()

    def describe_provider(self, provider_id: str) -> StaticCapabilityManifest:
        """Returns the authoritative static capability manifest for a provider."""
        return self.catalog.describe_provider(provider_id)

    def is_provider_available(self, provider_id: str) -> tuple[bool, str]:
        """Checks if optional driver/dependencies are installed for a provider."""
        strategy = self.catalog.get_strategy(provider_id)
        return strategy.is_dependency_available()

    def validate_endpoint_spec(self, spec: EndpointSpec) -> None:
        """
        Validates that an endpoint specification conforms to provider parameters.
        Raises ValueError or ConfigurationError on invalid parameters.
        """
        strategy = self.catalog.get_strategy(spec.provider_id)
        strategy.validate_configuration(spec)

    def compute_fingerprint(self, spec: EndpointSpec) -> EndpointBindingFingerprint:
        """Computes a deterministic, secret-free binding fingerprint for an endpoint spec."""
        return compute_endpoint_fingerprint(spec)

    # =========================================================================
    # 2. PUBLIC / SANITIZED DIAGNOSTIC & PROBE OPERATIONS
    # =========================================================================

    def test_connectivity(self, spec: EndpointSpec) -> ConnectionTestResult:
        """
        Executes end-to-end connection testing with latency breakdown across DNS, TCP, TLS, and Auth.
        """
        return self._connectivity_probe.test_connectivity(spec)

    def attest_endpoint_identity(self, spec: EndpointSpec) -> PhysicalEndpointIdentity:
        """
        Connects ephemerally and captures live verified physical facts (versions, cluster, catalog, topology).
        """
        req = SessionRequest(purpose=SessionPurpose.DISCOVERY, endpoint_spec=spec)
        handle, route = self.session_factory.create_physical_session(req)
        strategy = self.catalog.get_strategy(spec.provider_id)
        try:
            return strategy.attest_physical_identity(handle.physical_connection, spec, route)
        finally:
            strategy.close(handle.physical_connection)
            route.close()

    def probe_permissions(
        self,
        spec: EndpointSpec,
        purpose: SessionPurpose = SessionPurpose.PERMISSION_PROBE,
    ) -> PermissionSnapshot:
        """
        Probes live authorization privileges for the specified execution purpose.
        """
        return self._permission_probe.probe_permissions(spec, purpose)

    def probe_capabilities(self, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        """
        Probes live server features and engine capabilities against an active database session.
        """
        return self._capability_probe.probe_capabilities(spec)

    def get_health(self, spec: EndpointSpec) -> ConnectionHealthSnapshot:
        """Checks real-time health, RTT, and operational responsiveness of an endpoint."""
        return self._health_probe.check_health(spec)

    def get_pressure(self, spec: EndpointSpec) -> ConnectionPressureSnapshot:
        """Measures real-time pool checkout wait, utilization, active counts, and saturation."""
        return self._pressure_probe.get_pressure(spec)

    def detect_drift(
        self,
        spec: EndpointSpec,
        baseline_identity: PhysicalEndpointIdentity,
    ) -> DriftReport:
        """
        Compares baseline attested identity with live facts to detect IP, version, topology, or cert drift.
        If drift requires pool invalidation, invalidates affected pools automatically.
        """
        current_identity = self.attest_endpoint_identity(spec)
        baseline_fp = compute_endpoint_fingerprint(spec).fingerprint_sha256
        report = DriftDetector.compare_identities(
            baseline=baseline_identity,
            current=current_identity,
            baseline_fingerprint=baseline_fp,
            current_fingerprint=baseline_fp,
        )
        if report.requires_pool_invalidation:
            logger.warning(
                f"[ConnectionAuthority] Material drift detected ({report.drift_type.value}). Invalidating pools for '{baseline_fp}'."
            )
            self.invalidate_endpoint(baseline_fp)

        return report

    def get_pool_snapshot(
        self,
        spec: EndpointSpec,
        purpose: Optional[SessionPurpose] = None,
    ) -> Optional[PoolSnapshot]:
        """Returns snapshot statistics for an endpoint connection pool."""
        cat_gen = self.catalog.get_catalog_generation() if hasattr(self.catalog, "get_catalog_generation") else 1
        fp = compute_endpoint_fingerprint(spec, catalog_generation=cat_gen).fingerprint_sha256
        return self.pool_manager.get_pool_snapshot(fp, purpose)

    def get_all_pool_snapshots(self) -> List[PoolSnapshot]:
        """Returns snapshots of all active pools across the current process."""
        return self.pool_manager.get_all_pool_snapshots()

    def invalidate_endpoint(self, spec_or_fingerprint: Union[EndpointSpec, str]) -> int:
        """Invalidates and destroys all connection pools matching the endpoint or fingerprint."""
        if isinstance(spec_or_fingerprint, EndpointSpec):
            cat_gen = self.catalog.get_catalog_generation() if hasattr(self.catalog, "get_catalog_generation") else 1
            fp = compute_endpoint_fingerprint(spec_or_fingerprint, catalog_generation=cat_gen).fingerprint_sha256
        else:
            fp = str(spec_or_fingerprint)
        return self.pool_manager.invalidate_endpoint(fp)

    def invalidate_all(self) -> int:
        """Invalidates all pools across all endpoints."""
        return self.pool_manager.invalidate_all()

    # =========================================================================
    # 3. INTERNAL ENGINE OPERATIONS (FOR FUTURE ENGINE AUTHORITIES)
    # =========================================================================

    def acquire_session_lease(
        self,
        request: SessionRequest,
        borrower_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        policy: Optional[PoolPolicy] = None,
    ) -> SessionLease:
        """
        Acquires a scoped, purpose-specific physical session lease for Engine task execution.
        Enforces fail-closed capability satisfaction checks before acquisition.
        """
        # 1. Full fail-closed admission validation (role, required capabilities, required privileges, restrictions)
        self.capability_resolver.validate_admission(request)

        # 2. Acquire lease from pool manager
        return self.pool_manager.acquire_session(
            request=request,
            borrower_id=borrower_id,
            timeout_seconds=timeout_seconds,
            policy=policy,
        )

    def validate_lease(self, lease: SessionLease) -> bool:
        """Validates that a session lease remains active and physically healthy."""
        if not lease.is_valid():
            return False
        strategy = self.catalog.get_strategy(lease.provider_id)
        raw_conn = lease.get_physical_handle()
        if raw_conn is not None:
            try:
                return strategy.validate(raw_conn)
            except Exception:
                return False
        return True

    def renew_lease(self, lease: SessionLease, extension_seconds: float = 300.0) -> SessionLease:
        """Extends expiration deadline of an active session lease."""
        if not lease.is_valid():
            raise RuntimeError(f"Cannot renew invalid or closed lease '{lease.lease_id}'.")
        import time
        new_expires = (lease.expires_at_epoch or time.time()) + extension_seconds
        return SessionLease(
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

    def release_session_lease(self, lease: SessionLease) -> bool:
        """
        Releases a session lease, executes transaction rollback and session reset,
        and returns clean connection to pool.
        """
        return self.pool_manager.release_session(lease)

    def invalidate_session(self, lease: SessionLease) -> None:
        """Destroys an invalid, failed, or poisoned session immediately."""
        strategy = self.catalog.get_strategy(lease.provider_id)
        if lease._internal_handle:
            from akaalEngine.connection.sessions.reset import SessionResetManager
            SessionResetManager.destroy_poisoned_session(lease._internal_handle, strategy)


# Global default connection authority instance
default_connection_authority = ConnectionAuthority.get_instance()
