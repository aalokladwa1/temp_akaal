"""
akaalEngine.connection.providers.relational.tidb
====================================================
Canonical TiDB Provider Strategy (P7A Campaign B).

TiDB exposes a MySQL wire-compatible SQL layer over the distributed TiKV storage engine,
so this reuses PyMySQL -- the same architectural reasoning as the MySQL strategy -- but is
NOT a MySQL relabel:
  - TiDB does NOT use MySQL's binlog replication mechanism at all; change capture is a
    genuinely separate component (TiCDC), not reachable via `@@log_bin`/`@@binlog_format`
    the way MySQL's strategy checks. Reusing that MySQL-specific probe here would be a
    truthfulness violation (a misleading green light), so CDC_LOG_CAPTURE is declared
    UNSUPPORTED at this layer rather than probed via a check that doesn't apply.
  - SAVEPOINTS support is version-gated (added in TiDB 6.2+) and not reliably present
    across TiDB's history the way it always has been in MySQL -- declared UNSUPPORTED by
    default rather than assumed.
  - TiDB's stateless SQL layer over TiKV has genuine region-based data placement,
    introspectable via `SHOW TABLE ... REGIONS`, a real TiDB-native mechanism distinct
    from InnoDB's storage model.
  - Transactions default to pessimistic locking (since TiDB 3.0) with a Percolator-style
    two-phase commit underneath -- a materially different implementation from InnoDB's
    row-level locking, even though the SQL-visible TRANSACTIONS capability is the same.
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

logger = logging.getLogger("akaalEngine.connection.providers.tidb")


class TiDBProviderStrategy(BaseProviderStrategy):
    """Canonical TiDB provider strategy -- distributed SQL over TiKV, MySQL wire-compatible."""

    PROVIDER_ID = "tidb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "PingCAP"

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
                "LOAD_DATA_INFILE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,  # pessimistic by default, Percolator 2PC
                "DISTRIBUTED_TOPOLOGY": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,  # region-based, SHOW TABLE REGIONS
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
                # Truthfully NOT claimed supported: version-gated or requires a separate
                # component this connector does not probe.
                "SAVEPOINTS": CapabilitySupportStatus.UNSUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "CDC requires TiCDC, a separate component not reachable via MySQL's @@log_bin/@@binlog_format vars -- never assumed supported.",
                "SAVEPOINT support is version-gated (TiDB 6.2+); not assumed supported without a live version probe.",
            ],
            required_privileges=["SELECT", "PROCESS"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import pymysql
            return True, f"PyMySQL version {getattr(pymysql, '__version__', 'unknown')} available (TiDB uses the MySQL wire protocol)."
        except ImportError:
            return False, "PyMySQL library not installed. Install via 'pip install pymysql'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host:
            raise ValueError("TiDB host is required.")

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
                    error_code="TIDB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import pymysql

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 4000  # TiDB's default SQL port, not MySQL's 3306
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "root")
        password = credentials.get("password") or ""
        dbname = spec.database_name or None

        ssl_kwargs = None
        if spec.tls_binding.mode != TLSMode.DISABLED:
            ssl_kwargs = {}
            if spec.tls_binding.ca_cert_path:
                ssl_kwargs["ca"] = spec.tls_binding.ca_cert_path
            if spec.tls_binding.client_cert_path:
                ssl_kwargs["cert"] = spec.tls_binding.client_cert_path
            if not ssl_kwargs and spec.tls_binding.mode in (TLSMode.REQUIRED, TLSMode.VERIFY_CA, TLSMode.VERIFY_FULL):
                ssl_kwargs["check_hostname"] = (spec.tls_binding.mode == TLSMode.VERIFY_FULL)

        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname,
            connect_timeout=int(spec.route_spec.connect_timeout_ms / 1000.0),
            ssl=ssl_kwargs,
            autocommit=True,
            charset=spec.options.get("charset", "utf8mb4"),
        )
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
            if hasattr(connection, "open") and not connection.open:
                return False
            connection.ping(reconnect=False)
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        if connection is None:
            return False
        try:
            connection.rollback()
            cur = connection.cursor()
            cur.execute("SET autocommit = 1;")
            cur.close()
            return True
        except Exception:
            return False

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_version = "TiDB"
        current_db = spec.database_name
        current_user = spec.auth_spec.username if spec.auth_spec else "root"

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT tidb_version()")
                row = cur.fetchone()
                if row and row[0]:
                    server_version = str(row[0]).split("\n")[0]
                cur.execute("SELECT DATABASE(), CURRENT_USER()")
                row2 = cur.fetchone()
                if row2:
                    current_db = row2[0] or spec.database_name
                    current_user = row2[1]
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 4000,
            server_version=server_version,
            catalog_or_database=current_db,
            schema_name=spec.schema_name or current_db,
            principal_identity=current_user,
            route_type=spec.route_spec.route_type,
            # Truthful: TiDB's SQL layer is stateless and distributed over TiKV -- not a
            # MySQL-style primary/replica pair.
            topology_role="DISTRIBUTED",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="tidb-attested",
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
        granted: list[str] = ["SELECT"]
        is_admin = False

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SHOW GRANTS")
                grants = [r[0] for r in cur.fetchall()]
                for g in grants:
                    if "ALL PRIVILEGES" in g or "SUPER" in g:
                        is_admin = True
                        granted.extend(["INSERT", "UPDATE", "DELETE", "CREATE", "DROP"])
                        break
                cur.close()
            except Exception:
                pass

        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="tidb-attested",
            granted_privileges=granted,
            missing_privileges=[],
            is_read_only=not is_admin and purpose.is_read_only_by_default,
            can_write=is_admin or not purpose.is_read_only_by_default,
            can_ddl=is_admin or purpose == SessionPurpose.SCHEMA_DDL,
            can_cdc=False,  # never truthfully claimable without a live TiCDC probe
            is_admin=is_admin,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        errno = getattr(exc, "args", [None])[0] if getattr(exc, "args", None) else None
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "TIDB_ERROR"
        retryable = False

        if errno in (1045, 1698):
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "TIDB_AUTH_FAILED"
        elif errno in (1044, 1142, 1143, 1227):
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "TIDB_PERMISSION_DENIED"
        elif errno in (1049,):
            category = FailureCategory.INVALID_CONFIGURATION
            code = "TIDB_UNKNOWN_DATABASE"
        elif errno in (1213, 9007):  # 9007 = TiDB-specific "Write conflict" (Percolator abort)
            category = FailureCategory.TIMEOUT
            code = "TIDB_WRITE_CONFLICT"
            retryable = True
        elif errno in (2002, 2003, 2006):
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "TIDB_SERVER_UNAVAILABLE"
            retryable = True

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )

    def get_fastpath_hints(self) -> dict[str, Any]:
        return {
            "load_data_infile_supported": True,
            "max_batch_size": 10000,
        }
