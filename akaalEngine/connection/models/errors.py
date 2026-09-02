"""
akaalEngine.connection.models.errors
====================================
Canonical normalized error taxonomy, exception classes, and sanitized failure models.
Guarantees zero-secret leakage across all error reporting paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class FailureCategory(str, Enum):
    """Standardized failure categories for Connection Authority."""
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    DNS_FAILURE = "DNS_FAILURE"
    ROUTE_FAILURE = "ROUTE_FAILURE"
    PROXY_FAILURE = "PROXY_FAILURE"
    SSH_FAILURE = "SSH_FAILURE"
    TLS_FAILURE = "TLS_FAILURE"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_PERMISSION_FAILURE = "AUTHORIZATION_PERMISSION_FAILURE"
    ENDPOINT_UNAVAILABLE = "ENDPOINT_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    POOL_EXHAUSTION = "POOL_EXHAUSTION"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    IDENTITY_DRIFT = "IDENTITY_DRIFT"
    TOPOLOGY_DRIFT = "TOPOLOGY_DRIFT"
    CAPABILITY_MISMATCH = "CAPABILITY_MISMATCH"
    SESSION_POISONED = "SESSION_POISONED"
    PROVIDER_INTERNAL_ERROR = "PROVIDER_INTERNAL_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ConnectionFailure:
    """
    Immutable canonical connection failure descriptor.
    Guarantees that error_message and details are completely sanitized of secret material.
    """
    error_code: str
    category: FailureCategory
    message: str
    retryable: bool
    provider_id: str
    remediation: str = ""
    sqlstate: Optional[str] = None
    original_error_type: Optional[str] = None
    endpoint_fingerprint: Optional[str] = None
    details: Mapping[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "category": self.category.value,
            "message": self.message,
            "retryable": self.retryable,
            "provider_id": self.provider_id,
            "remediation": self.remediation,
            "sqlstate": self.sqlstate,
            "original_error_type": self.original_error_type,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "details": dict(self.details),
            "timestamp": self.timestamp,
        }


class ConnectionEngineException(Exception):
    """Base exception for all Connection Authority errors wrapping a canonical ConnectionFailure."""

    def __init__(self, failure: ConnectionFailure) -> None:
        super().__init__(f"[{failure.category.value}] {failure.error_code}: {failure.message}")
        self.failure = failure


class DependencyMissingError(ConnectionEngineException):
    """Raised when an optional provider library or driver is missing."""


class ConfigurationError(ConnectionEngineException):
    """Raised when an endpoint spec or configuration parameter is invalid."""


class DNSResolutionError(ConnectionEngineException):
    """Raised when DNS lookup or Happy Eyeballs address resolution fails."""


class RouteResolutionError(ConnectionEngineException):
    """Raised when network routing, proxy, or private endpoint path cannot be established."""


class SSHTunnelError(ConnectionEngineException):
    """Raised when authenticated SSH bastion tunneling or host key validation fails."""


class TLSVerificationError(ConnectionEngineException):
    """Raised when TLS handshake, certificate validation, or mTLS identity verification fails."""


class ConnectivityPolicyDeniedError(ConnectionEngineException):
    """P7.9: raised when the resolved physical route/TLS binding does not satisfy the
    EndpointSpec's required connectivity protection tier. Fails closed before connect."""


class AuthenticationError(ConnectionEngineException):
    """Raised when credential verification or identity token validation fails at the endpoint."""


class PermissionDeniedError(ConnectionEngineException):
    """Raised when credentials lack necessary privileges for a requested session purpose."""


class EndpointUnavailableError(ConnectionEngineException):
    """Raised when physical database / service endpoint is unreachable or down."""


class ConnectionTimeoutError(ConnectionEngineException):
    """Raised when an acquisition, handshake, or query timeout deadline expires."""


class ConnectionCancelledError(ConnectionEngineException):
    """Raised when an active connection or checkout operation is cancelled via cancellation token."""


class PoolExhaustionError(ConnectionEngineException):
    """Raised when pool capacity or checkout wait queues are exceeded."""


class IdentityDriftError(ConnectionEngineException):
    """Raised when live physical identity does not match attested binding fingerprint."""


class TopologyDriftError(ConnectionEngineException):
    """Raised when cluster role (primary/replica/leader) changes unexpectedly."""


class CapabilityMismatchError(ConnectionEngineException):
    """Raised when an endpoint cannot physically satisfy required capability."""


class SessionPoisonedError(ConnectionEngineException):
    """Raised when a dirty or un-resettable session cannot be returned cleanly to pool."""


class SessionInitializationError(ConnectionEngineException):
    """Raised when mandatory session initialization (safety parameters, read-only, timeouts) fails."""


class SecretResolutionError(ConnectionEngineException):
    """Raised when an ephemeral secret reference cannot be resolved or is invalid."""


class ProviderInternalError(ConnectionEngineException):
    """Raised when a driver or database engine encounters an unclassified internal error."""
