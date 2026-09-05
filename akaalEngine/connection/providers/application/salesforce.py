"""
akaalEngine.connection.providers.application.salesforce
=========================================================
Canonical Salesforce Provider Strategy (P7A Campaign B, provider #46).

Salesforce is a SaaS/application platform accessed via REST/SOQL/SObject Collections --
NOT a SQL database, and SObjects are not modeled as relational tables with fabricated
PK/FK/transaction semantics. Connects via `simple_salesforce` (the de facto standard
Salesforce Python client), authenticating with username/password+security-token or an
OAuth2 access token, whichever credentials are supplied.
"""

from __future__ import annotations

import logging
import ssl
from typing import Any, Mapping, Optional, Tuple

from akaalEngine.connection.models.capability import (
    CapabilitySupportStatus,
    PermissionSnapshot,
    ProbedCapabilitySnapshot,
    ProofLevel,
    StaticCapabilityManifest,
)
from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec
from akaalEngine.connection.models.errors import (
    ConfigurationError,
    ConnectionFailure,
    FailureCategory,
    DependencyMissingError,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.salesforce")


class SalesforceProviderStrategy(BaseProviderStrategy):
    """Canonical Salesforce provider strategy -- SaaS/application platform, not a database."""

    PROVIDER_ID = "salesforce"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "application"
    VENDOR_NAME = "Salesforce, Inc."

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE, EndpointRole.VALIDATION],
            supports_tls=True,
            supports_mtls=False,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,  # SObject Describe metadata
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,  # SOQL query + nextRecordsUrl
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,  # SObject Collections (<=200/call)
                "TRANSACTIONS": CapabilitySupportStatus.UNSUPPORTED,  # no ACID transaction concept in the REST API
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,  # SObject relationship/reference fields
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,  # Platform Events/CDC not implemented here
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "Bulk API 2.0 (for very large extracts) is not implemented -- only SOQL query()/query_more().",
                "SObject Collections writes are capped at 200 records/call; no server-side transaction spans multiple calls.",
            ],
            required_privileges=["api", "refresh_token"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import simple_salesforce
            return True, "simple_salesforce SDK available."
        except ImportError:
            return False, "'simple_salesforce' SDK not installed. Install via 'pip install simple-salesforce'."

    def connect(
        self,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
        credentials: Mapping[str, Any],
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> Any:
        avail, msg = self.is_dependency_available()
        if not avail:
            raise DependencyMissingError(
                ConnectionFailure(
                    error_code="SALESFORCE_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from simple_salesforce import Salesforce

        domain = spec.options.get("domain", "login")
        access_token = credentials.get("access_token")
        instance_url = credentials.get("instance_url") or spec.options.get("instance_url")

        if access_token and instance_url:
            return Salesforce(instance_url=instance_url, session_id=access_token)

        username = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        password = credentials.get("password")
        security_token = credentials.get("security_token", "")
        consumer_key = credentials.get("consumer_key")
        consumer_secret = credentials.get("consumer_secret")

        if not username or not password:
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="SALESFORCE_MISSING_CREDENTIALS",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message="Salesforce requires either (access_token + instance_url) or (username + password [+ security_token]).",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        kwargs: dict[str, Any] = {"username": username, "password": password, "security_token": security_token, "domain": domain}
        if consumer_key and consumer_secret:
            kwargs["consumer_key"] = consumer_key
            kwargs["consumer_secret"] = consumer_secret
        return Salesforce(**kwargs)

    def close(self, connection: Any) -> None:
        pass  # simple_salesforce is HTTP-based; no persistent socket to close

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            connection.query("SELECT Id FROM Organization LIMIT 1")
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return True  # stateless REST session, nothing session-local to reset

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        instance_url = getattr(connection, "sf_instance", None) or spec.host or "salesforce.com"
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=instance_url,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version=f"Salesforce API v{getattr(connection, 'sf_version', 'unknown')}",
            catalog_or_database=None,
            route_type=spec.route_spec.route_type,
            topology_role="MANAGED_SAAS_PLATFORM",
        )

    def probe_capabilities(self, connection: Any, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="salesforce-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(self, connection: Any, spec: EndpointSpec, purpose: SessionPurpose) -> PermissionSnapshot:
        granted: list[str] = []
        if connection is not None:
            try:
                connection.query("SELECT Id FROM Organization LIMIT 1")
                granted = ["api"]
            except Exception:
                granted = []
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="salesforce-attested",
            granted_privileges=granted,
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=not purpose.is_read_only_by_default,
            can_ddl=False,
            can_cdc=False,
            is_admin=False,
        )

    def normalize_error(self, exc: Exception, stage: str = "EXECUTION") -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "SALESFORCE_ERROR"
        retryable = False
        if "SalesforceAuthenticationFailed" in exc_name or "INVALID_LOGIN" in msg:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "SALESFORCE_AUTH_FAILED"
        elif "SalesforceExpiredSession" in exc_name:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "SALESFORCE_SESSION_EXPIRED"
            retryable = True
        elif "REQUEST_LIMIT_EXCEEDED" in msg or "429" in msg:
            category = FailureCategory.TIMEOUT
            code = "SALESFORCE_RATE_LIMITED"
            retryable = True
        elif "INSUFFICIENT_ACCESS" in msg or "FORBIDDEN" in msg:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "SALESFORCE_PERMISSION_DENIED"
        elif "timeout" in msg.lower() or "connection" in msg.lower():
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "SALESFORCE_UNAVAILABLE"
            retryable = True
        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )
