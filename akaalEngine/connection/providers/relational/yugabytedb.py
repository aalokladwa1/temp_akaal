"""
akaalEngine.connection.providers.relational.yugabytedb
==========================================================
Canonical YugabyteDB Provider Strategy (P7A Campaign B, YSQL API).

YugabyteDB exposes a PostgreSQL-wire-compatible YSQL API (built on the distributed DocDB
storage layer), so this reuses `psycopg2` -- the same architectural reasoning as the
CockroachDB strategy -- but is NOT a CockroachDB or PostgreSQL relabel:
  - YugabyteDB genuinely supports Change Data Capture via the PostgreSQL logical
    replication protocol (`pg_replication_slots` with the `yboutput`/`pgoutput` plugin),
    a real and different mechanism from CockroachDB's Enterprise-licensed CHANGEFEED --
    probed truthfully rather than assumed.
  - Distributed transaction conflicts surface as SQLSTATE 40001, the same as
    CockroachDB/PostgreSQL convention, but the underlying cause is DocDB's distributed
    transaction manager (Raft-replicated tablets), not a single-node MVCC engine.
  - Tablet-based (not simple range-based) sharding is the real distribution unit.
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

logger = logging.getLogger("akaalEngine.connection.providers.yugabytedb")


class YugabyteDBProviderStrategy(BaseProviderStrategy):
    """Canonical YugabyteDB provider strategy -- distributed SQL, YSQL (PostgreSQL wire-compatible)."""

    PROVIDER_ID = "yugabytedb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "Yugabyte, Inc."

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
                "SERIALIZABLE_RETRY_REQUIRED": CapabilitySupportStatus.SUPPORTED,
                "DISTRIBUTED_TOPOLOGY": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,  # tablet-based sharding
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                "LOBS": CapabilitySupportStatus.SUPPORTED,
                # Truthfully NOT claimed supported without a live replication-slot probe:
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "CDC_LOG_CAPTURE requires an active pg_replication_slots entry with the yboutput/pgoutput plugin, not assumed supported without a live probe.",
                "SQLSTATE 40001 requires whole-transaction retry (distributed transaction conflict), not statement-level retry.",
            ],
            required_privileges=["CONNECT", "USAGE", "SELECT"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import psycopg2
            return True, f"psycopg2 version {getattr(psycopg2, '__version__', 'unknown')} available (YugabyteDB YSQL uses the PostgreSQL wire protocol)."
        except ImportError:
            return False, "psycopg2 library not installed. Install via 'pip install psycopg2-binary'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host:
            raise ValueError("YugabyteDB host is required.")
        if not spec.database_name:
            raise ValueError("YugabyteDB database_name is required.")

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
                    error_code="YUGABYTEDB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import psycopg2

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 5433  # YugabyteDB's default YSQL port
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "yugabyte")
        password = credentials.get("password") or ""
        dbname = spec.database_name or "yugabyte"

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
        server_version = "YugabyteDB"
        current_db = spec.database_name
        current_user = spec.auth_spec.username if spec.auth_spec else "yugabyte"

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT version(), current_database(), current_user")
                row = cur.fetchone()
                if row:
                    server_version = row[0]
                    current_db = row[1]
                    current_user = row[2]
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 5433,
            server_version=server_version,
            catalog_or_database=current_db,
            schema_name=spec.schema_name or "public",
            principal_identity=current_user,
            route_type=spec.route_spec.route_type,
            # Truthful: YugabyteDB is a tablet-sharded distributed cluster over DocDB, not
            # a primary/replica pair.
            topology_role="DISTRIBUTED",
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
            "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNKNOWN,
        }
        if connection:
            try:
                cur = connection.cursor()
                # YugabyteDB CDC is exposed via PostgreSQL-protocol replication slots with
                # the yboutput (or pgoutput-compatible) plugin -- probe truthfully.
                cur.execute("SELECT plugin FROM pg_replication_slots WHERE plugin IN ('yboutput', 'pgoutput')")
                rows = cur.fetchall()
                caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.SUPPORTED if rows else CapabilitySupportStatus.UNSUPPORTED
                cur.close()
            except Exception:
                # No privilege to view replication slots, or view absent -- fail closed.
                caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED

        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="yugabytedb-attested",
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
        is_admin = False
        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
                row = cur.fetchone()
                is_admin = bool(row and row[0])
                if is_admin:
                    granted.extend(["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP"])
                else:
                    granted.append("SELECT")
                    if not purpose.is_read_only_by_default:
                        granted.extend(["INSERT", "UPDATE", "DELETE"])
                cur.close()
            except Exception:
                granted.append("SELECT")

        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="yugabytedb-attested",
            granted_privileges=granted,
            missing_privileges=[],
            is_read_only=not is_admin and purpose.is_read_only_by_default,
            can_write=is_admin or not purpose.is_read_only_by_default,
            can_ddl=is_admin or purpose == SessionPurpose.SCHEMA_DDL,
            can_cdc=False,  # never truthfully claimable without the replication-slot probe above
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
        code = "YUGABYTEDB_ERROR"
        retryable = False

        if sqlstate in ("28P01", "28000"):
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "YUGABYTEDB_AUTH_FAILED"
            retryable = False
        elif sqlstate in ("42501",):
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "YUGABYTEDB_PERMISSION_DENIED"
            retryable = False
        elif sqlstate in ("3D000",):
            category = FailureCategory.INVALID_CONFIGURATION
            code = "YUGABYTEDB_DATABASE_NOT_FOUND"
            retryable = False
        elif sqlstate == "40001":
            # YugabyteDB's distributed transaction conflict signal (DocDB transaction
            # manager) -- routine under concurrent load, whole transaction must be
            # retried by the caller.
            category = FailureCategory.TIMEOUT
            code = "YUGABYTEDB_TRANSACTION_CONFLICT"
            retryable = True
        elif sqlstate in ("57P01", "57P03"):
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "YUGABYTEDB_TSERVER_UNAVAILABLE"
            retryable = True
        elif "timeout" in msg.lower():
            category = FailureCategory.TIMEOUT
            code = "YUGABYTEDB_TIMEOUT"
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
