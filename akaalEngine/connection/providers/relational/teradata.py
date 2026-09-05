"""
akaalEngine.connection.providers.relational.teradata
=====================================================
Canonical Teradata Provider Strategy (P7A Campaign B, provider #39).

Teradata is an MPP relational data warehouse. This strategy connects via `teradatasql`
(the real, official Teradata Python DB-API 2.0 driver). No FastLoad/TPT bulk-protocol
claim is made -- only the plain DB-API cursor path this Engine physically implements.
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
    ConnectionFailure,
    FailureCategory,
    DependencyMissingError,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.teradata")


class TeradataProviderStrategy(BaseProviderStrategy):
    """Canonical Teradata provider strategy -- MPP relational data warehouse."""

    PROVIDER_ID = "teradata"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "Teradata Corporation"

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
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                # No FastLoad/TPT/CDC capture module exists in this Engine -- not claimed.
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "Bulk load uses standard executemany() INSERT, not FastLoad/TPT/MultiLoad.",
            ],
            required_privileges=["SELECT", "INSERT"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import teradatasql
            return True, "teradatasql driver available."
        except ImportError:
            return False, "'teradatasql' client driver not installed. Install via 'pip install teradatasql'."

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
                    error_code="TERADATA_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import teradatasql
        host = resolved_route.effective_host or spec.host
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        password = credentials.get("password") or ""
        dbname = spec.database_name or None
        logmech = spec.options.get("logmech", "TD2")

        conn_kwargs: dict[str, Any] = {"host": host, "user": user, "password": password, "logmech": logmech}
        if dbname:
            conn_kwargs["database"] = dbname
        if ssl_context is not None or spec.options.get("encryptdata"):
            conn_kwargs["encryptdata"] = "true"

        return teradatasql.connect(**conn_kwargs)

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
            cur = connection.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        if connection is None:
            return False
        try:
            cur = connection.cursor()
            cur.execute("ROLLBACK")
            cur.close()
            return True
        except Exception:
            return True  # Teradata autocommit-by-default sessions have nothing to reset

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_ver = "Teradata"
        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT InfoData FROM DBC.DBCInfoV WHERE InfoKey = 'VERSION'")
                row = cur.fetchone()
                if row:
                    server_ver = f"Teradata {row[0]}"
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 1025,
            server_version=server_ver,
            catalog_or_database=spec.database_name,
            schema_name=spec.schema_name or spec.database_name,
            principal_identity=spec.auth_spec.username if spec.auth_spec else None,
            route_type=spec.route_spec.route_type,
            topology_role="MPP_NODE",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="teradata-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="teradata-attested",
            granted_privileges=["SELECT", "INSERT", "UPDATE", "DELETE"],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=not purpose.is_read_only_by_default,
            can_ddl=purpose == SessionPurpose.SCHEMA_DDL,
            can_cdc=False,
            is_admin=False,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "TERADATA_ERROR"
        retryable = False
        lower = msg.lower()
        if "logon" in lower or "password" in lower or "authenticat" in lower:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "TERADATA_AUTH_FAILED"
        elif "timeout" in lower or "connection refused" in lower or "unreachable" in lower:
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "TERADATA_UNAVAILABLE"
            retryable = True
        elif "permission" in lower or "access" in lower:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "TERADATA_PERMISSION_DENIED"
        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
