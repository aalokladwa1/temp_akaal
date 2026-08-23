"""
akaalEngine.connection.providers.relational.postgresql
======================================================
Canonical PostgreSQL Provider Strategy.
Supports psycopg2 / asyncpg native drivers, binary COPY fast-path, logical decoding CDC, and SQLSTATE error normalization.
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
from akaalEngine.connection.models.endpoint import EndpointRole, EndpointSpec, TLSMode
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

logger = logging.getLogger("akaalEngine.connection.providers.postgresql")


class PostgreSQLProviderStrategy(BaseProviderStrategy):
    """
    Canonical PostgreSQL provider strategy.
    """

    PROVIDER_ID = "postgresql"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "PostgreSQL Global Development Group"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.REFERENCE, EndpointRole.VALIDATION, EndpointRole.CDC_LOG],
            supports_tls=True,
            supports_mtls=True,
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "BINARY_COPY": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,  # via pgoutput / test_decoding
                "LOGICAL_REPLICATION": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                "LOBS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=["Requires wal_level=logical for CDC capture"],
            required_privileges=["CONNECT", "USAGE", "SELECT", "REPLICATION"],
            fastpath_features=["COPY FROM STDIN BINARY", "UNLOGGED TABLES", "SESSION REPLICATION ROLE"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import psycopg2
            return True, f"psycopg2 version {getattr(psycopg2, '__version__', 'unknown')} available."
        except ImportError:
            return False, "psycopg2 library not installed. Install via 'pip install psycopg2-binary'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host:
            raise ValueError("PostgreSQL host is required.")
        if not spec.database_name:
            raise ValueError("PostgreSQL database_name is required.")

    def connect(
        self,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
        credentials: Mapping[str, Any],
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> Any:
        avail, msg = self.is_dependency_available()
        if not avail:
            failure = ConnectionFailure(
                error_code="POSTGRES_DEPENDENCY_MISSING",
                category=FailureCategory.DEPENDENCY_MISSING,
                message=msg,
                retryable=False,
                provider_id=self.PROVIDER_ID,
            )
            raise DependencyMissingError(failure)

        import psycopg2

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 5432
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "postgres")
        password = credentials.get("password") or ""
        dbname = spec.database_name or "postgres"

        # Determine sslmode
        sslmode = "prefer"
        if spec.tls_binding.mode == TLSMode.DISABLED:
            sslmode = "disable"
        elif spec.tls_binding.mode == TLSMode.REQUIRED:
            sslmode = "require"
        elif spec.tls_binding.mode == TLSMode.VERIFY_CA:
            sslmode = "verify-ca"
        elif spec.tls_binding.mode == TLSMode.VERIFY_FULL:
            sslmode = "verify-full"

        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            sslmode=sslmode,
            sslrootcert=spec.tls_binding.ca_cert_path,
            sslcert=spec.tls_binding.client_cert_path,
            connect_timeout=int(spec.route_spec.connect_timeout_ms / 1000.0),
            application_name="akaalEngine",
        )
        conn.autocommit = True
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
            if hasattr(connection, "closed") and connection.closed != 0:
                return False
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
            cur.execute("DISCARD ALL; SET standard_conforming_strings = on;")
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
        server_version = "PostgreSQL"
        cluster_name = None
        current_db = spec.database_name
        current_user = spec.auth_spec.username if spec.auth_spec else "postgres"

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT version(), current_database(), current_user, pg_is_in_recovery()")
                row = cur.fetchone()
                if row:
                    server_version = row[0]
                    current_db = row[1]
                    current_user = row[2]
                    is_replica = row[3]
                    topo_role = "REPLICA" if is_replica else "PRIMARY"
                else:
                    topo_role = "PRIMARY"
                cur.close()
            except Exception:
                topo_role = "PRIMARY"
        else:
            topo_role = "PRIMARY"

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 5432,
            server_version=server_version,
            server_cluster_name=cluster_name,
            catalog_or_database=current_db,
            schema_name=spec.schema_name or "public",
            principal_identity=current_user,
            route_type=spec.route_spec.route_type,
            topology_role=topo_role,
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        caps = {
            "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
            "BULK_READ": CapabilitySupportStatus.SUPPORTED,
            "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
            "BINARY_COPY": CapabilitySupportStatus.SUPPORTED,
            "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
            "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNKNOWN,
        }
        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SHOW wal_level")
                wal_val = cur.fetchone()[0]
                if wal_val.lower() == "logical":
                    caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.SUPPORTED
                else:
                    caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED
                cur.close()
            except Exception:
                pass

        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="pg-attested",
            capabilities=caps,
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        granted: list[str] = ["CONNECT"]
        missing: list[str] = []
        is_admin = False

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT usesuper FROM pg_user WHERE usename = current_user")
                row = cur.fetchone()
                if row and row[0]:
                    is_admin = True
                    granted.extend(["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "REPLICATION"])
                else:
                    granted.extend(["SELECT"])
                    if not purpose.is_read_only_by_default:
                        granted.extend(["INSERT", "UPDATE", "DELETE"])
                cur.close()
            except Exception:
                granted.append("SELECT")

        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="pg-attested",
            granted_privileges=granted,
            missing_privileges=missing,
            is_read_only=not is_admin and purpose.is_read_only_by_default,
            can_write=is_admin or not purpose.is_read_only_by_default,
            can_ddl=is_admin or purpose == SessionPurpose.SCHEMA_DDL,
            can_cdc=is_admin,
            is_admin=is_admin,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        sqlstate = getattr(exc, "pgcode", getattr(exc, "sqlstate", None))
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "POSTGRES_ERROR"
        retryable = False

        if sqlstate in ("28P01", "28000"):
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "POSTGRES_AUTH_FAILED"
            retryable = False
        elif sqlstate in ("42501",):
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "POSTGRES_PERMISSION_DENIED"
            retryable = False
        elif sqlstate in ("3D000",):
            category = FailureCategory.INVALID_CONFIGURATION
            code = "POSTGRES_DATABASE_NOT_FOUND"
            retryable = False
        elif sqlstate in ("40001", "40P01"):  # Serialization failure / Deadlock
            category = FailureCategory.TIMEOUT
            code = "POSTGRES_SERIALIZATION_FAILURE"
            retryable = True
        elif sqlstate in ("53200", "53000", "53100"):  # Out of memory / Lock table full
            category = FailureCategory.POOL_EXHAUSTION
            code = "POSTGRES_CAPACITY_EXHAUSTED"
            retryable = False
        elif sqlstate in ("57P01", "57P02", "57P03"):  # Admin shutdown / Crash shutdown
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "POSTGRES_SERVER_SHUTDOWN"
            retryable = True
        elif "timeout" in msg.lower():
            category = FailureCategory.TIMEOUT
            code = "POSTGRES_TIMEOUT"
            retryable = True

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            sqlstate=sqlstate,
            original_error_type=exc_name,
        )

    def get_fastpath_hints(self) -> dict[str, Any]:
        return {
            "binary_copy_supported": True,
            "max_batch_size": 10000,
            "supports_parallel_workers": True,
        }
