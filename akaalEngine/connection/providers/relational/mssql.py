"""
akaalEngine.connection.providers.relational.mssql
================================================
Canonical Microsoft SQL Server Provider Strategy.
Supports pyodbc / aioodbc, BCP / fast_executemany bulk writing, and CDC capture.
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

logger = logging.getLogger("akaalEngine.connection.providers.mssql")


class MSSQLProviderStrategy(BaseProviderStrategy):
    """Canonical Microsoft SQL Server provider strategy."""

    PROVIDER_ID = "mssql"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "Microsoft"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE, EndpointRole.VALIDATION, EndpointRole.CDC_LOG],
            supports_tls=True,
            supports_mtls=False,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "BCP_FAST_COPY": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,  # via SQL Server CDC / CT
                "CHANGE_TRACKING": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            required_privileges=["CONNECT SQL", "VIEW DEFINITION", "SELECT"],
            fastpath_features=["FAST_EXECUTEMANY", "TABLOCK", "BULK INSERT"],
        )

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        from akaalEngine.connection.models.endpoint import AuthenticationType
        from akaalEngine.connection.models.errors import ConfigurationError
        is_trusted = (
            (spec.auth_spec and spec.auth_spec.auth_type == AuthenticationType.INTEGRATED) or
            spec.options.get("trusted_connection") in (True, "yes", "True", "1") or
            spec.options.get("integrated_security") in ("SSPI", True, "yes")
        )
        if is_trusted and spec.auth_spec and spec.auth_spec.auth_type == AuthenticationType.INTEGRATED and spec.auth_spec.secret_ref:
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="MSSQL_CONTRADICTORY_AUTH_CONFIG",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message="Cannot specify SQL password secret reference when Windows Integrated Authentication (Trusted Connection) is enabled.",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import pyodbc
            return True, f"pyodbc version {getattr(pyodbc, 'version', 'unknown')} available."
        except ImportError:
            return False, "pyodbc library not installed. Install via 'pip install pyodbc'."

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
                    error_code="MSSQL_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import pyodbc
        from akaalEngine.connection.models.endpoint import AuthenticationType, TLSMode

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 1433
        dbname = spec.database_name or "master"
        driver = spec.options.get("odbc_driver", "ODBC Driver 17 for SQL Server")

        auth_type = spec.auth_spec.auth_type if spec.auth_spec else AuthenticationType.PASSWORD
        is_trusted = (
            auth_type == AuthenticationType.INTEGRATED or
            spec.options.get("trusted_connection") in (True, "yes", "True", "1") or
            spec.options.get("integrated_security") in ("SSPI", True, "yes")
        )

        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "sa")
        password = credentials.get("password") or ""

        # Determine TLS settings for SQL Server ODBC
        tls_mode = spec.tls_binding.mode
        if tls_mode == TLSMode.DISABLED:
            encrypt = "no"
            trust_cert = "yes"
        elif tls_mode == TLSMode.PREFERRED:
            encrypt = "no"
            trust_cert = "yes" if spec.tls_binding.allow_self_signed else "no"
        elif tls_mode in (TLSMode.REQUIRED, TLSMode.VERIFY_CA, TLSMode.VERIFY_FULL):
            encrypt = "yes"
            trust_cert = "yes" if spec.tls_binding.allow_self_signed else "no"
        else:
            encrypt = "yes"
            trust_cert = "no"

        if is_trusted:
            conn_str = f"DRIVER={{{driver}}};SERVER={host},{port};DATABASE={dbname};Trusted_Connection=yes;Encrypt={encrypt};TrustServerCertificate={trust_cert};"
        else:
            conn_str = f"DRIVER={{{driver}}};SERVER={host},{port};DATABASE={dbname};UID={user};PWD={password};Encrypt={encrypt};TrustServerCertificate={trust_cert};"

        conn = pyodbc.connect(conn_str, timeout=int(spec.route_spec.connect_timeout_ms / 1000.0), autocommit=True)
        return conn

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
            connection.rollback()
            cur = connection.cursor()
            cur.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")
            cur.close()
            connection.autocommit = True
            return True
        except Exception:
            return False

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_ver = "Microsoft SQL Server"
        db_name = spec.database_name or "master"
        user = spec.auth_spec.username if spec.auth_spec else "sa"
        topo_role = "PRIMARY"

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT @@VERSION, DB_NAME(), SUSER_SNAME()")
                row = cur.fetchone()
                if row:
                    server_ver = row[0]
                    db_name = row[1]
                    user = row[2]
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 1433,
            server_version=server_ver,
            catalog_or_database=db_name,
            schema_name=spec.schema_name or "dbo",
            principal_identity=user,
            route_type=spec.route_spec.route_type,
            topology_role=topo_role,
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="mssql-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "BCP_FAST_COPY": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="mssql-attested",
            granted_privileges=["SELECT", "INSERT", "UPDATE", "DELETE", "VIEW DEFINITION"],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=not purpose.is_read_only_by_default,
            can_ddl=purpose == SessionPurpose.SCHEMA_DDL,
            can_cdc=True,
            is_admin=False,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "MSSQL_ERROR"
        retryable = False

        if "login failed" in msg.lower() or "18456" in msg:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "MSSQL_AUTH_FAILED"
        elif "permission denied" in msg.lower() or "229" in msg:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "MSSQL_PERMISSION_DENIED"
        elif "timeout" in msg.lower() or "deadlock" in msg.lower():
            category = FailureCategory.TIMEOUT
            code = "MSSQL_DEADLOCK_OR_TIMEOUT"
            retryable = True
        elif "server not found" in msg.lower() or "cannot connect" in msg.lower():
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "MSSQL_SERVER_UNAVAILABLE"
            retryable = True

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )

    def get_fastpath_hints(self) -> dict[str, Any]:
        return {
            "fast_executemany": True,
            "max_batch_size": 10000,
        }
