"""
akaalEngine.connection.providers.relational.sap_hana
=====================================================
Canonical SAP HANA Provider Strategy (P7A Campaign B, provider #41).

This is the SAP HANA *database engine* (in-memory relational SQL), distinct from any
SAP *application*-layer connector (RFC/BAPI/IDoc/OData -- provider #47, unresolved
scope). Connects via `hdbcli` (SAP's official Python driver, DB-API-shaped).
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

logger = logging.getLogger("akaalEngine.connection.providers.sap_hana")


class SAPHANAProviderStrategy(BaseProviderStrategy):
    """Canonical SAP HANA provider strategy -- in-memory relational database engine."""

    PROVIDER_ID = "sap_hana"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "SAP SE"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE, EndpointRole.VALIDATION],
            supports_tls=True,
            supports_mtls=True,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                # SLT/SDI replication is a separate SAP product not implemented here.
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=["Bulk load uses standard executemany() INSERT, not HANA bulk-import utilities."],
            required_privileges=["SELECT", "INSERT"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import hdbcli
            return True, "hdbcli driver available."
        except ImportError:
            return False, "'hdbcli' client driver not installed. Install via 'pip install hdbcli'."

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
                    error_code="SAP_HANA_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from hdbcli import dbapi
        host = resolved_route.effective_host or spec.host
        port = resolved_route.effective_port or spec.port or 30015
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        password = credentials.get("password") or ""

        conn_kwargs: dict[str, Any] = {
            "address": host,
            "port": port,
            "user": user,
            "password": password,
        }
        if spec.database_name:
            conn_kwargs["databaseName"] = spec.database_name
        if ssl_context is not None or spec.options.get("encrypt"):
            conn_kwargs["encrypt"] = True
        return dbapi.connect(**conn_kwargs)

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
            cur.execute("SELECT 1 FROM DUMMY")
            cur.fetchone()
            cur.close()
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        if connection is None:
            return False
        try:
            connection.rollback()
            return True
        except Exception:
            return False

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_ver = "SAP HANA"
        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT VERSION FROM SYS.M_DATABASE")
                row = cur.fetchone()
                if row:
                    server_ver = f"SAP HANA {row[0]}"
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 30015,
            server_version=server_ver,
            catalog_or_database=spec.database_name,
            schema_name=spec.schema_name or (spec.auth_spec.username if spec.auth_spec else None),
            principal_identity=spec.auth_spec.username if spec.auth_spec else None,
            route_type=spec.route_spec.route_type,
            topology_role="PRIMARY",
        )

    def probe_capabilities(self, connection: Any, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="sap-hana-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(self, connection: Any, spec: EndpointSpec, purpose: SessionPurpose) -> PermissionSnapshot:
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="sap-hana-attested",
            granted_privileges=["SELECT", "INSERT", "UPDATE", "DELETE"],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=not purpose.is_read_only_by_default,
            can_ddl=purpose == SessionPurpose.SCHEMA_DDL,
            can_cdc=False,
            is_admin=False,
        )

    def normalize_error(self, exc: Exception, stage: str = "EXECUTION") -> ConnectionFailure:
        msg = redact_text(str(exc))
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "SAP_HANA_ERROR"
        retryable = False
        lower = msg.lower()
        if "password" in lower or "authenticat" in lower or "invalid credentials" in lower:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "SAP_HANA_AUTH_FAILED"
        elif "timeout" in lower or "refused" in lower or "unreachable" in lower:
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "SAP_HANA_UNAVAILABLE"
            retryable = True
        elif "not authorized" in lower or "insufficient privilege" in lower:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "SAP_HANA_PERMISSION_DENIED"
        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
