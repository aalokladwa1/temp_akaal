"""
akaalEngine.connection
======================
Authority #1: Connection Authority for akaalEngine.
Owns physical establishment, session-level truth, capability negotiation,
identity attestation, and process-local pooling between AKAAL and all endpoints.
"""

from akaalEngine.connection.api.authority import (
    ConnectionAuthority,
    default_connection_authority,
)

from akaalEngine.connection.models.endpoint import (
    EndpointRole,
    AuthenticationType,
    AuthenticationSpec,
    TLSMode,
    TLSBinding,
    RouteType,
    RouteSpec,
    EndpointSpec,
)

from akaalEngine.connection.models.identity import (
    DriftType,
    DriftSeverity,
    EndpointBindingFingerprint,
    PhysicalEndpointIdentity,
    DriftReport,
)

from akaalEngine.connection.models.capability import (
    CapabilitySupportStatus,
    ProofLevel,
    CapabilityDescriptor,
    StaticCapabilityManifest,
    ProbedCapabilitySnapshot,
    PermissionSnapshot,
)

from akaalEngine.connection.models.session import (
    SessionPurpose,
    IsolationLevel,
    SessionRequest,
    InternalSessionHandle,
    SessionLease,
)

from akaalEngine.connection.models.health import (
    HealthState,
    ConnectionTestResult,
    ConnectionHealthSnapshot,
    ConnectionPressureSnapshot,
    PoolSnapshot,
)

from akaalEngine.connection.models.errors import (
    FailureCategory,
    ConnectionFailure,
    ConnectionEngineException,
    DependencyMissingError,
    ConfigurationError,
    DNSResolutionError,
    RouteResolutionError,
    SSHTunnelError,
    TLSVerificationError,
    AuthenticationError,
    PermissionDeniedError,
    EndpointUnavailableError,
    ConnectionTimeoutError,
    ConnectionCancelledError,
    PoolExhaustionError,
    IdentityDriftError,
    TopologyDriftError,
    CapabilityMismatchError,
    SessionPoisonedError,
    ProviderInternalError,
)

from akaalEngine.connection.catalog.provider_catalog import (
    ProviderCatalog,
    default_provider_catalog,
)

from akaalEngine.connection.catalog.capability_resolver import (
    CapabilityResolver,
    default_capability_resolver,
)

from akaalEngine.connection.pooling.manager import (
    PoolManager,
    default_pool_manager,
)

from akaalEngine.connection.pooling.policy import (
    PoolPolicy,
)

from akaalEngine.connection.security.secret_consumer import (
    ResolvedSecret,
    SecretConsumer,
    default_secret_consumer,
)

from akaalEngine.connection.security.redaction import (
    redact_text,
    redact_url,
    redact_mapping,
)

__all__ = [
    # Canonical Façade
    "ConnectionAuthority",
    "default_connection_authority",
    # Models
    "EndpointRole",
    "AuthenticationType",
    "AuthenticationSpec",
    "TLSMode",
    "TLSBinding",
    "RouteType",
    "RouteSpec",
    "EndpointSpec",
    "DriftType",
    "DriftSeverity",
    "EndpointBindingFingerprint",
    "PhysicalEndpointIdentity",
    "DriftReport",
    "CapabilitySupportStatus",
    "ProofLevel",
    "CapabilityDescriptor",
    "StaticCapabilityManifest",
    "ProbedCapabilitySnapshot",
    "PermissionSnapshot",
    "SessionPurpose",
    "IsolationLevel",
    "SessionRequest",
    "InternalSessionHandle",
    "SessionLease",
    "HealthState",
    "ConnectionTestResult",
    "ConnectionHealthSnapshot",
    "ConnectionPressureSnapshot",
    "PoolSnapshot",
    # Errors
    "FailureCategory",
    "ConnectionFailure",
    "ConnectionEngineException",
    "DependencyMissingError",
    "ConfigurationError",
    "DNSResolutionError",
    "RouteResolutionError",
    "SSHTunnelError",
    "TLSVerificationError",
    "AuthenticationError",
    "PermissionDeniedError",
    "EndpointUnavailableError",
    "ConnectionTimeoutError",
    "ConnectionCancelledError",
    "PoolExhaustionError",
    "IdentityDriftError",
    "TopologyDriftError",
    "CapabilityMismatchError",
    "SessionPoisonedError",
    "ProviderInternalError",
    # Catalog
    "ProviderCatalog",
    "default_provider_catalog",
    "CapabilityResolver",
    "default_capability_resolver",
    # Pooling
    "PoolManager",
    "default_pool_manager",
    "PoolPolicy",
    # Security
    "ResolvedSecret",
    "SecretConsumer",
    "default_secret_consumer",
    "redact_text",
    "redact_url",
    "redact_mapping",
]
