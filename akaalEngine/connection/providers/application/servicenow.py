"""
akaalEngine.connection.providers.application.servicenow
=========================================================
Canonical ServiceNow Provider Strategy (P7A Campaign B, provider #48).

ServiceNow is a SaaS/application platform accessed via the Table REST API -- NOT a SQL
database. The physical connection handle returned is a real `requests.Session`
pre-configured with the instance base URL and Basic or OAuth2 bearer authentication --
the actual object the Transport driver's `db_connection`/`session` parameter expects
(see transport/drivers/servicenow.py).
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

logger = logging.getLogger("akaalEngine.connection.providers.servicenow")


class ServiceNowProviderStrategy(BaseProviderStrategy):
    """Canonical ServiceNow provider strategy -- SaaS/application platform, not a database."""

    PROVIDER_ID = "servicenow"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "application"
    VENDOR_NAME = "ServiceNow, Inc."

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
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,  # sys_dictionary table metadata
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,  # Table API sysparm_offset/limit
                "BULK_WRITE": CapabilitySupportStatus.UNSUPPORTED,  # per-record POST/PUT only, no bulk endpoint used here
                "TRANSACTIONS": CapabilitySupportStatus.UNSUPPORTED,  # no ACID transaction concept in the REST API
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,  # reference fields
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,  # sys_updated_on polling is NOT CDC
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "Writes are per-record Table API calls, not a bulk Import Set/Attachment API executor.",
                "Incremental reads use sys_updated_on polling, which is honestly NOT change-data-capture.",
            ],
            required_privileges=["rest_api_explorer", "web_service_admin"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import requests
            return True, "requests library available."
        except ImportError:
            return False, "'requests' library not installed. Install via 'pip install requests'."

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
                    error_code="SERVICENOW_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import requests

        instance = spec.options.get("instance") or spec.host
        if not instance:
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="SERVICENOW_MISSING_INSTANCE",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message="ServiceNow requires an 'instance' hostname (spec.host or spec.options['instance']).",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )
        base_url = instance if instance.startswith("http") else f"https://{instance}.service-now.com"

        session = requests.Session()
        session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

        access_token = credentials.get("access_token")
        if access_token:
            session.headers["Authorization"] = f"Bearer {access_token}"
        else:
            username = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
            password = credentials.get("password")
            if not username or not password:
                raise ConfigurationError(
                    ConnectionFailure(
                        error_code="SERVICENOW_MISSING_CREDENTIALS",
                        category=FailureCategory.INVALID_CONFIGURATION,
                        message="ServiceNow requires either an OAuth2 access_token or (username + password).",
                        retryable=False,
                        provider_id=self.PROVIDER_ID,
                    )
                )
            session.auth = (username, password)

        session.base_url = base_url  # duck-typed convenience attribute consumed by the Transport driver
        return session

    def close(self, connection: Any) -> None:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            base = getattr(connection, "base_url", "")
            resp = connection.get(f"{base}/api/now/table/sys_user", params={"sysparm_limit": 1})
            return bool(resp is not None and getattr(resp, "status_code", 500) < 400)
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
        base = getattr(connection, "base_url", spec.host or "service-now.com")
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=base,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version="ServiceNow Table API",
            catalog_or_database=None,
            route_type=spec.route_spec.route_type,
            topology_role="MANAGED_SAAS_PLATFORM",
        )

    def probe_capabilities(self, connection: Any, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="servicenow-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(self, connection: Any, spec: EndpointSpec, purpose: SessionPurpose) -> PermissionSnapshot:
        granted: list[str] = []
        if connection is not None and self.validate(connection):
            granted = ["read"]
            if not purpose.is_read_only_by_default:
                granted.append("write")
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="servicenow-attested",
            granted_privileges=granted,
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write="write" in granted,
            can_ddl=False,
            can_cdc=False,
            is_admin=False,
        )

    def normalize_error(self, exc: Exception, stage: str = "EXECUTION") -> ConnectionFailure:
        msg = redact_text(str(exc))
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "SERVICENOW_ERROR"
        retryable = False
        status_code = getattr(exc, "response", None)
        status_code = getattr(status_code, "status_code", None) if status_code is not None else None
        if status_code == 401:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "SERVICENOW_AUTH_FAILED"
        elif status_code == 403:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "SERVICENOW_PERMISSION_DENIED"
        elif status_code == 429:
            category = FailureCategory.TIMEOUT
            code = "SERVICENOW_RATE_LIMITED"
            retryable = True
        elif status_code == 404:
            category = FailureCategory.INVALID_CONFIGURATION
            code = "SERVICENOW_NOT_FOUND"
        elif "timeout" in msg.lower() or "connection" in msg.lower():
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "SERVICENOW_UNAVAILABLE"
            retryable = True
        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
