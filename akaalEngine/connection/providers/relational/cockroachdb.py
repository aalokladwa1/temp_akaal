"""
akaalEngine.connection.providers.relational.cockroachdb
==========================================================
Canonical CockroachDB Provider Strategy (P7A Campaign B, provider #31).

CockroachDB speaks the PostgreSQL wire protocol, so this reuses `psycopg2` (already the
canonical PostgreSQL driver in this Engine, and already installed) rather than inventing a
new driver dependency -- but this is NOT the PostgreSQL strategy relabeled. CockroachDB's
distributed-transaction model is materially different and is handled truthfully, not
inherited blindly:
  - SQLSTATE 40001 ("restart transaction") is CockroachDB's NORMAL, EXPECTED serialization
    conflict signal under its Serializable-only isolation model -- it is not an occasional
    deadlock as in PostgreSQL, it is the routine cost of distributed optimistic concurrency,
    and callers are expected to retry the whole transaction, not just re-issue one statement.
  - There is no primary/replica "topology_role" concept the way PostgreSQL has
    `pg_is_in_recovery()` -- CockroachDB is a leaderless-per-range distributed cluster; this
    provider reports topology truthfully as "DISTRIBUTED", not a fabricated "PRIMARY".
  - CDC (CHANGEFEEDs) requires an Enterprise license and explicit cluster configuration this
    Engine cannot verify without a live connection with sufficient privilege -- declared
    UNSUPPORTED, not SUPPORTED, until a real probe can prove it (see probe_capabilities).
  - No `wal_level`/logical-replication concept exists in CockroachDB at all -- the
    PostgreSQL-specific CDC prerequisite check is not carried over.
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

logger = logging.getLogger("akaalEngine.connection.providers.cockroachdb")


class CockroachDBProviderStrategy(BaseProviderStrategy):
    """Canonical CockroachDB provider strategy -- distributed SQL, PostgreSQL wire-compatible."""

    PROVIDER_ID = "cockroachdb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "Cockroach Labs"

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
                "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,  # cockroach nested-txn savepoints
                "DISTRIBUTED_TOPOLOGY": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                "LOBS": CapabilitySupportStatus.SUPPORTED,
                # Truthfully NOT claimed supported without a live, licensed, privileged probe:
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,  # CHANGEFEED requires Enterprise license + probe
                "BINARY_COPY": CapabilitySupportStatus.UNSUPPORTED,  # Cockroach's COPY differs from Postgres binary COPY internals
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "CHANGEFEED (CDC) requires an Enterprise license and is not assumed supported without a live probe.",
                "SQLSTATE 40001 requires whole-transaction retry, not statement-level retry.",
            ],
            required_privileges=["CONNECT", "USAGE", "SELECT"],
            fastpath_features=["IMPORT INTO (bulk load, requires cluster/userfile access)"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import psycopg2
            return True, f"psycopg2 version {getattr(psycopg2, '__version__', 'unknown')} available (CockroachDB uses the PostgreSQL wire protocol)."
        except ImportError:
            return False, "psycopg2 library not installed. Install via 'pip install psycopg2-binary'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host:
            raise ValueError("CockroachDB host is required.")
        if not spec.database_name:
            raise ValueError("CockroachDB database_name is required.")

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
                error_code="COCKROACHDB_DEPENDENCY_MISSING",
                category=FailureCategory.DEPENDENCY_MISSING,
                message=msg,
                retryable=False,
                provider_id=self.PROVIDER_ID,
            )
            raise DependencyMissingError(failure)

        import psycopg2

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 26257  # CockroachDB's default SQL port, not 5432
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "root")
        password = credentials.get("password") or ""
        dbname = spec.database_name or "defaultdb"

        # CockroachDB clusters (Cockroach Cloud in particular) commonly require TLS by
        # default -- "prefer" would silently downgrade against a cluster that mandates it,
        # so the default here is stricter than PostgreSQL's.
        sslmode = "verify-full"
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
        server_version = "CockroachDB"
        current_db = spec.database_name
        current_user = spec.auth_spec.username if spec.auth_spec else "root"
        cluster_id = None

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT version(), current_database(), current_user")
                row = cur.fetchone()
                if row:
                    server_version = row[0]
                    current_db = row[1]
                    current_user = row[2]
                try:
                    cur.execute("SHOW CLUSTER SETTING cluster.organization")
                    org_row = cur.fetchone()
                    if org_row:
                        cluster_id = org_row[0]
                except Exception:
                    pass  # not all deployments expose this setting to the connecting user
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 26257,
            server_version=server_version,
            server_cluster_name=cluster_id,
            catalog_or_database=current_db,
            schema_name=spec.schema_name or "public",
            principal_identity=current_user,
            route_type=spec.route_spec.route_type,
            # Truthful: CockroachDB is a leaderless distributed cluster, not a
            # primary/replica pair -- reporting "PRIMARY" (PostgreSQL's convention) here
            # would misrepresent the actual topology.
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
            "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
            "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNKNOWN,
        }
        if connection:
            try:
                cur = connection.cursor()
                # CHANGEFEED requires the Enterprise license; probe truthfully rather than
                # assuming either way.
                cur.execute("SHOW CLUSTER SETTING enterprise.license")
                license_row = cur.fetchone()
                if license_row and license_row[0]:
                    caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.SUPPORTED
                else:
                    caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED
                cur.close()
            except Exception:
                # No privilege to view the setting, or setting absent (core/no license) --
                # fail closed to UNSUPPORTED rather than guessing SUPPORTED.
                caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED

        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="cockroachdb-attested",
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
                cur.execute("SHOW GRANTS ON ROLE current_user")
                rows = cur.fetchall()
                role_options = {str(r[1]).upper() for r in rows if len(r) > 1}
                is_admin = "ADMIN" in role_options or "CREATEROLE" in role_options
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
            endpoint_fingerprint="cockroachdb-attested",
            granted_privileges=granted,
            missing_privileges=missing,
            is_read_only=not is_admin and purpose.is_read_only_by_default,
            can_write=is_admin or not purpose.is_read_only_by_default,
            can_ddl=is_admin or purpose == SessionPurpose.SCHEMA_DDL,
            can_cdc=False,  # never truthfully claimable without the license probe above
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
        code = "COCKROACHDB_ERROR"
        retryable = False

        if sqlstate in ("28P01", "28000"):
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "COCKROACHDB_AUTH_FAILED"
            retryable = False
        elif sqlstate in ("42501",):
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "COCKROACHDB_PERMISSION_DENIED"
            retryable = False
        elif sqlstate in ("3D000",):
            category = FailureCategory.INVALID_CONFIGURATION
            code = "COCKROACHDB_DATABASE_NOT_FOUND"
            retryable = False
        elif sqlstate == "40001":
            # CockroachDB's routine serializable-conflict signal -- expected under normal
            # load, NOT the same severity as PostgreSQL's occasional deadlock. Whole
            # transaction must be retried by the caller, not just the failing statement.
            category = FailureCategory.TIMEOUT
            code = "COCKROACHDB_TRANSACTION_RETRY_REQUIRED"
            retryable = True
        elif sqlstate in ("57P01", "57P03"):
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "COCKROACHDB_NODE_UNAVAILABLE"
            retryable = True
        elif "timeout" in msg.lower():
            category = FailureCategory.TIMEOUT
            code = "COCKROACHDB_TIMEOUT"
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
            "binary_copy_supported": False,
            "max_batch_size": 5000,  # CockroachDB recommends smaller batches than PostgreSQL COPY due to range-split behavior
            "supports_parallel_workers": True,
        }
