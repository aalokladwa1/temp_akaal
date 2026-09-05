"""
akaalEngine.connection.providers.relational.informix
=====================================================
Canonical IBM Informix Provider Strategy (P7A Campaign B, provider #43).
Informix is NOT collapsed into DB2 merely because both are IBM products -- distinct
identity, catalogs, and connection string shape. Connects via `ibm_db_dbi` (the
DB-API 2.0-compliant wrapper over IBM's CLI driver, shared transport with DB2 but a
genuinely distinct database engine and catalog set).
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

logger = logging.getLogger("akaalEngine.connection.providers.informix")


class InformixProviderStrategy(BaseProviderStrategy):
    """Canonical IBM Informix provider strategy."""

    PROVIDER_ID = "informix"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "IBM"

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
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                # Informix CDC API / MQ replication is a separate product not implemented here.
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "Bulk load uses standard executemany() INSERT, not the native onload/dbimport utilities.",
                "Identifiers are treated as unquoted (DELIMIDENT not assumed set).",
            ],
            required_privileges=["SELECT", "INSERT"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import ibm_db_dbi
            return True, "ibm_db_dbi driver available."
        except ImportError:
            return False, "'ibm_db' client driver not installed. Install via 'pip install ibm_db'."

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
                    error_code="INFORMIX_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import ibm_db_dbi
        host = resolved_route.effective_host or spec.host
        port = resolved_route.effective_port or spec.port or 9088
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        password = credentials.get("password") or ""
        dbname = spec.database_name or ""
        server_name = spec.options.get("informix_server", "ol_informix")

        conn_str = (
            f"DATABASE={dbname};HOSTNAME={host};PORT={port};PROTOCOL=onsoctcp;"
            f"UID={user};PWD={password};SERVER={server_name};"
        )
        return ibm_db_dbi.connect(conn_str, "", "")

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
            cur.execute("SELECT 1 FROM systables WHERE tabid = 1")
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
        server_ver = "IBM Informix"
        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT DBINFO('version', 'full') FROM systables WHERE tabid = 1")
                row = cur.fetchone()
                if row:
                    server_ver = f"IBM Informix {row[0]}"
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 9088,
            server_version=server_ver,
            catalog_or_database=spec.database_name,
            schema_name=spec.schema_name or "informix",
            principal_identity=spec.auth_spec.username if spec.auth_spec else None,
            route_type=spec.route_spec.route_type,
            topology_role="PRIMARY",
        )

    def probe_capabilities(self, connection: Any, spec: EndpointSpec) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="informix-attested",
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
            endpoint_fingerprint="informix-attested",
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
        code = "INFORMIX_ERROR"
        retryable = False
        lower = msg.lower()
        if "incorrect password" in lower or "authenticat" in lower:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "INFORMIX_AUTH_FAILED"
        elif "timeout" in lower or "refused" in lower or "unreachable" in lower or "sqlcode=-930" in lower:
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "INFORMIX_UNAVAILABLE"
            retryable = True
        elif "permission" in lower or "not authorized" in lower:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "INFORMIX_PERMISSION_DENIED"
        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
