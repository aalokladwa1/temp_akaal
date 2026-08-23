"""
Unit tests verifying the 8 specific corrections of Authority #1 Connection.
==========================================================================
1. Routing & SSH Strict Host Verification & Route Lifecycle
2. Fail-Closed Session Admission across all 13 SessionPurposes & Bootstrap
3. Non-Weakening Purpose Restrictions & Mandatory Init Failure
4. Deterministic Pool Binding Identity & Secret Ref Differentiation
5. Fail-Closed Secret Lifecycle & In-Memory Wiping
6. Truthful Provider TLS Classification
7. Failure Normalization & Exception Taxonomy
8. ConnectionAuthority Full Integration Verification
"""

import pytest

from akaalEngine.connection.api.authority import ConnectionAuthority
from akaalEngine.connection.catalog.capability_resolver import CapabilityResolver
from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog
from akaalEngine.connection.identity.fingerprint import compute_endpoint_fingerprint
from akaalEngine.connection.models.capability import CapabilitySupportStatus, PermissionSnapshot
from akaalEngine.connection.models.endpoint import (
    AuthenticationSpec,
    AuthenticationType,
    EndpointRole,
    EndpointSpec,
    RouteSpec,
    RouteType,
    TLSBinding,
    TLSMode,
)
from akaalEngine.connection.models.errors import (
    CapabilityMismatchError,
    ConfigurationError,
    ConnectionEngineException,
    ConnectionFailure,
    DependencyMissingError,
    FailureCategory,
    RouteResolutionError,
    SecretResolutionError,
    SessionInitializationError,
    SSHTunnelError,
    TLSVerificationError,
)
from akaalEngine.connection.models.session import (
    InternalSessionHandle,
    IsolationLevel,
    SessionPurpose,
    SessionRequest,
)
from akaalEngine.connection.routing.resolver import RouteResolver
from akaalEngine.connection.routing.ssh import SSHTunnelRuntime
from akaalEngine.connection.security.secret_consumer import (
    InMemorySecretResolver,
    ResolvedSecret,
    SecretConsumer,
    create_testing_consumer,
    default_secret_consumer,
)
from akaalEngine.connection.sessions.factory import SessionFactory
from akaalEngine.connection.sessions.initialization import SessionInitializer
from akaalEngine.connection.sessions.reset import SessionResetManager


# =============================================================================
# CORRECTION 1: ROUTING & SSH VERIFICATION & LIFECYCLE
# =============================================================================

def test_socks_proxy_missing_host_fails_closed():
    """SOCKS5 proxy routing without proxy_host/proxy_port must fail closed with PROXY_HOST_PORT_REQUIRED."""
    resolver = RouteResolver()
    spec = EndpointSpec(
        provider_id="postgresql",
        host="db.internal",
        port=5432,
        route_spec=RouteSpec(
            route_type=RouteType.SOCKS5_PROXY,
            proxy_host=None,
            proxy_port=None,
        ),
    )
    with pytest.raises(RouteResolutionError) as exc_info:
        resolver.resolve_route(spec)
    assert exc_info.value.failure.error_code == "PROXY_HOST_PORT_REQUIRED"
    assert exc_info.value.failure.category == FailureCategory.PROXY_FAILURE


def test_sqlite_rejects_network_routes():
    """In-process SQLite provider must reject proxy and SSH routes fail-closed."""
    resolver = RouteResolver()
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=":memory:",
        route_spec=RouteSpec(route_type=RouteType.SSH_BASTION_TUNNEL, ssh_host="bastion.corp"),
    )
    with pytest.raises(RouteResolutionError) as exc_info:
        resolver.resolve_route(spec)
    assert exc_info.value.failure.error_code == "ROUTE_UNSUPPORTED_FOR_PROVIDER"


def test_ssh_strict_host_verification_fails_without_keys():
    """SSH tunnel without known_hosts or pinned fingerprint must fail closed under strict policy."""
    ssh_runtime = SSHTunnelRuntime()
    route_spec = RouteSpec(
        route_type=RouteType.SSH_BASTION_TUNNEL,
        ssh_host="bastion.example.com",
        ssh_port=22,
        allow_unverified_ssh=False,  # Strict default
    )
    with pytest.raises((SSHTunnelError, DependencyMissingError)) as exc_info:
        ssh_runtime.establish_tunnel(route_spec, target_host="db.internal", target_port=5432)
    assert exc_info.value.failure.error_code in ("SSH_STRICT_HOST_VERIFICATION_FAILED", "SSH_DEPENDENCY_MISSING")


def test_route_resource_lifetime_on_session_destruction():
    """Route resources tied to InternalSessionHandle must be closed upon session destruction."""
    class MockRouteResource:
        def __init__(self):
            self.closed = False
        def close(self):
            self.closed = True

    mock_route = MockRouteResource()
    handle = InternalSessionHandle(
        session_id="sess-test-01",
        fingerprint="fp123",
        purpose=SessionPurpose.BULK_SOURCE_READ,
        provider_id="sqlite",
        physical_connection=None,
        route_resource=mock_route,
    )

    catalog = ProviderCatalog.get_instance()
    strategy = catalog.get_strategy("sqlite")

    SessionResetManager.destroy_poisoned_session(handle, strategy)
    assert mock_route.closed is True
    assert handle.is_closed is True
    assert handle.route_resource is None


# =============================================================================
# CORRECTION 2: FAIL-CLOSED SESSION ADMISSION & BOOTSTRAP
# =============================================================================

def test_session_admission_probe_bootstrapping():
    """Health and Permission probes must bootstrap without circular permission dependencies."""
    resolver = CapabilityResolver()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")

    req_health = SessionRequest(purpose=SessionPurpose.HEALTH_PROBE, endpoint_spec=spec)
    req_perm = SessionRequest(purpose=SessionPurpose.PERMISSION_PROBE, endpoint_spec=spec)

    # Must succeed without raising CapabilityMismatchError
    resolver.validate_admission(req_health)
    resolver.validate_admission(req_perm)


def test_session_admission_role_mismatch():
    """Read-only roles like REFERENCE cannot execute writable purposes."""
    resolver = CapabilityResolver()
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=":memory:",
        role=EndpointRole.REFERENCE,
    )
    req = SessionRequest(purpose=SessionPurpose.BULK_TARGET_WRITE, endpoint_spec=spec)

    with pytest.raises(CapabilityMismatchError) as exc_info:
        resolver.validate_admission(req)
    assert exc_info.value.failure.error_code == "PURPOSE_ROLE_CONFLICT"


def test_session_admission_unsupported_required_capability():
    """Explicitly required capabilities not supported by the provider fail closed."""
    resolver = CapabilityResolver()
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    req = SessionRequest(
        purpose=SessionPurpose.BULK_SOURCE_READ,
        endpoint_spec=spec,
        required_capabilities=["NON_EXISTENT_SUPER_CAPABILITY"],
    )
    with pytest.raises(CapabilityMismatchError) as exc_info:
        resolver.validate_admission(req)
    assert exc_info.value.failure.error_code == "REQUIRED_CAPABILITY_UNSUPPORTED"


def test_session_admission_all_thirteen_purposes():
    """Admission validation covers all 13 SessionPurpose values truthfully."""
    resolver = CapabilityResolver()

    # Valid purposes for SQLite source/target
    valid_source_spec = EndpointSpec(provider_id="sqlite", database_name=":memory:", role=EndpointRole.SOURCE)
    valid_target_spec = EndpointSpec(provider_id="sqlite", database_name=":memory:", role=EndpointRole.TARGET)

    # SQLite supports discovery, metadata, schema_read, bulk_source_read, bulk_target_write, polling, validation_read, ddl, repair
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.DISCOVERY, endpoint_spec=valid_source_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.METADATA, endpoint_spec=valid_source_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.SCHEMA_READ, endpoint_spec=valid_source_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.BULK_SOURCE_READ, endpoint_spec=valid_source_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.BULK_TARGET_WRITE, endpoint_spec=valid_target_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.INCREMENTAL_POLLING, endpoint_spec=valid_source_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.VALIDATION_READ, endpoint_spec=valid_source_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.SCHEMA_DDL, endpoint_spec=valid_target_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.CDC_APPLY, endpoint_spec=valid_target_spec))
    resolver.validate_admission(SessionRequest(purpose=SessionPurpose.RECONCILIATION_REPAIR, endpoint_spec=valid_target_spec))

    # SQLite does NOT support CDC_LOG_CAPTURE (fails closed)
    with pytest.raises(CapabilityMismatchError) as exc_info:
        resolver.validate_admission(SessionRequest(purpose=SessionPurpose.CDC_CAPTURE, endpoint_spec=valid_source_spec))
    assert exc_info.value.failure.error_code == "CAPABILITY_CDC_UNSUPPORTED"


# =============================================================================
# CORRECTION 3: PURPOSE RESTRICTIONS & NON-WEAKENING READ-ONLY
# =============================================================================

def test_read_only_purpose_cannot_be_weakened():
    """Callers passing read_only=False on mandatory read-only purposes are rejected or enforced read-only."""
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    req = SessionRequest(
        purpose=SessionPurpose.VALIDATION_READ,
        endpoint_spec=spec,
        read_only=False,  # Attempted weakening
    )

    # is_effective_read_only() strictly preserves safety
    assert req.is_effective_read_only() is True

    # validate_restrictions() rejects caller weakening with ConfigurationError
    with pytest.raises(ConfigurationError):
        req.validate_restrictions()


# =============================================================================
# CORRECTION 4: DETERMINISTIC IDENTITY & NON-SECRET CREDENTIAL POINTERS
# =============================================================================

def test_fingerprint_includes_secret_references_without_collision():
    """Different secret_refs or token_refs must produce different fingerprints."""
    spec_a = EndpointSpec(
        provider_id="postgresql",
        host="db.corp",
        port=5432,
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.PASSWORD,
            username="app_user",
            secret_ref="vault://secret/creds-v1",
        ),
    )
    spec_b = EndpointSpec(
        provider_id="postgresql",
        host="db.corp",
        port=5432,
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.PASSWORD,
            username="app_user",
            secret_ref="vault://secret/creds-v2",
        ),
    )
    fp_a = compute_endpoint_fingerprint(spec_a).fingerprint_sha256
    fp_b = compute_endpoint_fingerprint(spec_b).fingerprint_sha256

    assert fp_a != fp_b, "Different secret_refs must not collide in fingerprint."


def test_fingerprint_includes_catalog_generation():
    """Bumping catalog generation produces a distinct fingerprint."""
    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    fp_gen1 = compute_endpoint_fingerprint(spec, catalog_generation=1).fingerprint_sha256
    fp_gen2 = compute_endpoint_fingerprint(spec, catalog_generation=2).fingerprint_sha256

    assert fp_gen1 != fp_gen2, "Catalog generation bump must differentiate fingerprints."


# =============================================================================
# CORRECTION 5: FAIL-CLOSED SECRET LIFECYCLE & IN-MEMORY WIPING
# =============================================================================

def test_secret_consumer_fails_closed_without_plaintext_fallback():
    """Unregistered or unresolved secret references fail closed with typed SecretResolutionError."""
    consumer = SecretConsumer()  # No resolver callback configured
    with pytest.raises(SecretResolutionError) as exc_info:
        consumer.resolve("vault://secret/db-password")
    assert exc_info.value.failure.error_code == "SECRET_RESOLVER_UNCONFIGURED"


def test_testing_consumer_resolves_and_wipes():
    """Testing secret consumer resolves truthfully and wipes memory representation."""
    consumer = create_testing_consumer({"vault://secret/test-key": "VERY_SENSITIVE_DATA_123"})
    resolved = consumer.resolve("vault://secret/test-key")
    assert resolved is not None
    assert resolved.get_value() == "VERY_SENSITIVE_DATA_123"

    # Wipe
    resolved.wipe()
    assert resolved.is_valid() is False
    with pytest.raises(RuntimeError, match="has already been wiped"):
        resolved.get_value()


# =============================================================================
# CORRECTION 6: TRUTHFUL PROVIDER TLS CLASSIFICATION
# =============================================================================

def test_sqlite_rejects_tls_configurations():
    """SQLite fails closed when configured with TLS."""
    catalog = ProviderCatalog.get_instance()
    strategy = catalog.get_strategy("sqlite")

    spec_tls = EndpointSpec(
        provider_id="sqlite",
        database_name=":memory:",
        tls_binding=TLSBinding(mode=TLSMode.REQUIRED),
    )
    with pytest.raises(TLSVerificationError) as exc_info:
        strategy.validate_configuration(spec_tls)
    assert exc_info.value.failure.error_code == "SQLITE_TLS_UNSUPPORTED"


# =============================================================================
# CORRECTION 7 & 8: AUTHORITY INTEGRATION VERIFICATION
# =============================================================================

def test_connection_authority_end_to_end_truth():
    """ConnectionAuthority operates truthfully end-to-end with active testing secrets."""
    default_secret_consumer.register_resolver(InMemorySecretResolver({"vault://secret/admin-pw": "admin123"}))
    authority = ConnectionAuthority.get_instance()

    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=":memory:",
        role=EndpointRole.SOURCE,
        auth_spec=AuthenticationSpec(
            auth_type=AuthenticationType.PASSWORD,
            username="admin",
            secret_ref="vault://secret/admin-pw",
        ),
    )

    # 1. Test connectivity
    res = authority.test_connectivity(spec)
    assert res.is_successful is True

    # 2. Acquire and release lease
    req = SessionRequest(purpose=SessionPurpose.BULK_SOURCE_READ, endpoint_spec=spec)
    lease = authority.acquire_session_lease(req, borrower_id="test-worker")
    assert lease.is_valid() is True
    assert authority.validate_lease(lease) is True

    # 3. Clean release
    released = authority.release_session_lease(lease)
    assert released is True
