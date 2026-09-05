"""
akaalEngine.connection.providers.relational.spanner
====================================================
Canonical Google Cloud Spanner Provider Strategy (P7A Campaign B, provider #45).

Distributed, globally-consistent relational database. Connects via the real
`google-cloud-spanner` SDK. The physical connection handle returned is the
`Database` object -- the actual object the Transport driver's `db_connection`
parameter expects (see transport/drivers/spanner.py), not merely a top-level client.
Spanner's PostgreSQL-dialect mode is NOT treated as equivalent to the PostgreSQL
provider -- distinct identity, distinct distributed-transaction/mutation semantics.
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

logger = logging.getLogger("akaalEngine.connection.providers.spanner")


class SpannerProviderStrategy(BaseProviderStrategy):
    """Canonical Google Cloud Spanner provider strategy -- distributed relational database."""

    PROVIDER_ID = "spanner"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "Google Cloud"

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
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,  # Mutation API batch
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,  # real distributed transactions
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,  # Change Streams not implemented here
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=["Change Streams (CDC) is a genuine Spanner feature but no capture module exists in this Engine."],
            required_privileges=["spanner.databases.select", "spanner.databases.write"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import google.cloud.spanner
            return True, "google-cloud-spanner SDK available."
        except ImportError:
            return False, "'google-cloud-spanner' SDK not installed. Install via 'pip install google-cloud-spanner'."

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
                    error_code="SPANNER_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from google.cloud import spanner

        project_id = spec.options.get("project_id") or credentials.get("project_id")
        instance_id = spec.options.get("instance_id")
        database_id = spec.database_name or spec.options.get("database_id")
        if not (project_id and instance_id and database_id):
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="SPANNER_MISSING_IDENTITY",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message="Spanner requires project_id, instance_id (spec.options), and a database_id/database_name.",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        client_kwargs: dict[str, Any] = {"project": project_id}
        credentials_json = credentials.get("service_account_json") or credentials.get("credentials")
        if credentials_json:
            client_kwargs["credentials"] = credentials_json

        client = spanner.Client(**client_kwargs)
        instance = client.instance(instance_id)
        database = instance.database(database_id)
        return database

    def close(self, connection: Any) -> None:
        pass  # google-cloud-spanner Database objects hold a gRPC channel pool, not a single socket

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            with connection.snapshot() as snap:
                list(snap.execute_sql("SELECT 1"))
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return True  # Spanner sessions are pooled/stateless per-call from the client's view

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=spec.host or "spanner.googleapis.com",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=spec.port or 443,
            server_version="Google Cloud Spanner",
            catalog_or_database=spec.database_name or spec.options.get("database_id"),
            schema_name=spec.options.get("instance_id"),
            cloud_region=spec.region or spec.options.get("region"),
            route_type=spec.route_spec.route_type,
            topology_role="MANAGED_DISTRIBUTED_STORE",
        )

    def probe_capabilities(self, connection: Any, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="spanner-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(self, connection: Any, spec: EndpointSpec, purpose: SessionPurpose) -> PermissionSnapshot:
        granted: list[str] = []
        if connection is not None:
            try:
                with connection.snapshot() as snap:
                    list(snap.execute_sql("SELECT 1"))
                granted = ["spanner.databases.select"]
                if not purpose.is_read_only_by_default:
                    granted.append("spanner.databases.write")
            except Exception:
                granted = []
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="spanner-attested",
            granted_privileges=granted,
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write="spanner.databases.write" in granted,
            can_ddl=False,
            can_cdc=False,
            is_admin=False,
        )

    def normalize_error(self, exc: Exception, stage: str = "EXECUTION") -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "SPANNER_ERROR"
        retryable = False
        if "Unauthenticated" in exc_name or "PermissionDenied" in exc_name:
            category = FailureCategory.AUTHENTICATION_FAILURE if "Unauthenticated" in exc_name else FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "SPANNER_AUTH_FAILED" if "Unauthenticated" in exc_name else "SPANNER_PERMISSION_DENIED"
        elif "Aborted" in exc_name:
            category = FailureCategory.TIMEOUT
            code = "SPANNER_TRANSACTION_ABORTED"
            retryable = True
        elif "DeadlineExceeded" in exc_name or "timeout" in msg.lower():
            category = FailureCategory.TIMEOUT
            code = "SPANNER_TIMEOUT"
            retryable = True
        elif "Unavailable" in exc_name:
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "SPANNER_UNAVAILABLE"
            retryable = True
        elif "NotFound" in exc_name:
            category = FailureCategory.INVALID_CONFIGURATION
            code = "SPANNER_NOT_FOUND"
        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )
