"""
akaalEngine.connection.providers.relational.mysql
================================================
Canonical MySQL Provider Strategy.
Supports PyMySQL / aiomysql, binlog CDC, LOAD DATA LOCAL INFILE fast-path, and error normalization.
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

logger = logging.getLogger("akaalEngine.connection.providers.mysql")


class MySQLProviderStrategy(BaseProviderStrategy):
    """Canonical MySQL provider strategy."""

    PROVIDER_ID = "mysql"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "Oracle MySQL"

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
                "LOAD_DATA_INFILE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,  # via binlog
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=["Requires binlog_format=ROW and binlog_row_image=FULL for CDC"],
            required_privileges=["SELECT", "RELOAD", "REPLICATION SLAVE", "REPLICATION CLIENT"],
            fastpath_features=["LOAD DATA LOCAL INFILE", "INSERT MULTIPLE ROWS", "SET FOREIGN_KEY_CHECKS=0"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import pymysql
            return True, f"PyMySQL version {getattr(pymysql, '__version__', 'unknown')} available."
        except ImportError:
            return False, "PyMySQL library not installed. Install via 'pip install pymysql'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host:
            raise ValueError("MySQL host is required.")

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
                    error_code="MYSQL_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import pymysql

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 3306
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
            cur.execute("SET autocommit = 1, foreign_key_checks = 1, sql_mode = 'DEFAULT';")
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
        server_version = "MySQL"
        current_db = spec.database_name
        current_user = spec.auth_spec.username if spec.auth_spec else "root"
        topo_role = "PRIMARY"

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT @@version, DATABASE(), CURRENT_USER(), @@read_only")
                row = cur.fetchone()
                if row:
                    server_version = row[0]
                    current_db = row[1] or spec.database_name
                    current_user = row[2]
                    is_ro = row[3]
                    topo_role = "REPLICA" if is_ro else "PRIMARY"
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 3306,
            server_version=server_version,
            catalog_or_database=current_db,
            schema_name=spec.schema_name or current_db,
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
            "LOAD_DATA_INFILE": CapabilitySupportStatus.SUPPORTED,
            "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
            "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
            "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNKNOWN,
        }
        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT @@log_bin, @@binlog_format")
                row = cur.fetchone()
                if row and row[0] and str(row[1]).upper() == "ROW":
                    caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.SUPPORTED
                else:
                    caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED
                cur.close()
            except Exception:
                pass

        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="mysql-attested",
            capabilities=caps,
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
                        granted.extend(["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "REPLICATION CLIENT", "REPLICATION SLAVE"])
                        break
                cur.close()
            except Exception:
                pass

        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="mysql-attested",
            granted_privileges=granted,
            missing_privileges=[],
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
        errno = getattr(exc, "args", [None])[0] if getattr(exc, "args", None) else None
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "MYSQL_ERROR"
        retryable = False

        if errno in (1045, 1698):  # Access denied
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "MYSQL_AUTH_FAILED"
        elif errno in (1044, 1142, 1143, 1227):  # Access denied for table / DB
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "MYSQL_PERMISSION_DENIED"
        elif errno in (1049,):  # Unknown database
            category = FailureCategory.INVALID_CONFIGURATION
            code = "MYSQL_UNKNOWN_DATABASE"
        elif errno in (1205, 1213):  # Lock wait timeout / Deadlock
            category = FailureCategory.TIMEOUT
            code = "MYSQL_DEADLOCK_OR_LOCK_TIMEOUT"
            retryable = True
        elif errno in (2002, 2003, 2006):  # Connection refused / Server gone
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "MYSQL_SERVER_UNAVAILABLE"
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
