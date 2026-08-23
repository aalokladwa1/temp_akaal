"""
akaalEngine.connection.models
=============================
Canonical immutable models and contracts for Connection Authority.
"""

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
    SessionInitializationError,
    SecretResolutionError,
    ProviderInternalError,
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

__all__ = [
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
    "SessionInitializationError",
    "SecretResolutionError",
    "ProviderInternalError",
    # Endpoint
    "EndpointRole",
    "AuthenticationType",
    "AuthenticationSpec",
    "TLSMode",
    "TLSBinding",
    "RouteType",
    "RouteSpec",
    "EndpointSpec",
    # Identity
    "DriftType",
    "DriftSeverity",
    "EndpointBindingFingerprint",
    "PhysicalEndpointIdentity",
    "DriftReport",
    # Capability
    "CapabilitySupportStatus",
    "ProofLevel",
    "CapabilityDescriptor",
    "StaticCapabilityManifest",
    "ProbedCapabilitySnapshot",
    "PermissionSnapshot",
    # Session
    "SessionPurpose",
    "IsolationLevel",
    "SessionRequest",
    "InternalSessionHandle",
    "SessionLease",
    # Health
    "HealthState",
    "ConnectionTestResult",
    "ConnectionHealthSnapshot",
    "ConnectionPressureSnapshot",
    "PoolSnapshot",
]
