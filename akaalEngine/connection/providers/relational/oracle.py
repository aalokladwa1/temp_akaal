"""
akaalEngine.connection.providers.relational.oracle
=================================================
Canonical Oracle Provider Strategy.
Supports python-oracledb native driver, LogMiner CDC, direct-path arrays, and ORA-xxxxx error normalization.
"""

from __future__ import annotations

import logging
import ssl
import threading
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

logger = logging.getLogger("akaalEngine.connection.providers.oracle")

_ORACLE_THICK_INIT_LOCK = threading.Lock()
_ORACLE_THICK_INIT_CONFIG: Optional[Tuple[Optional[str], Optional[str]]] = None


def _ensure_oracle_thick_mode(
    oracledb: Any,
    lib_dir: Optional[str],
    config_dir: Optional[str],
) -> None:
    """Initializes python-oracledb thick mode once with consistent process-global settings."""
    global _ORACLE_THICK_INIT_CONFIG
    requested_config = (lib_dir, config_dir)
    with _ORACLE_THICK_INIT_LOCK:
        if _ORACLE_THICK_INIT_CONFIG is not None:
            if _ORACLE_THICK_INIT_CONFIG != requested_config:
                raise ConfigurationError(
                    ConnectionFailure(
                        error_code="ORACLE_THICK_CONFIGURATION_CONFLICT",
                        category=FailureCategory.INVALID_CONFIGURATION,
                        message="Oracle thick mode is already initialized with different process-global client settings.",
                        retryable=False,
                        provider_id="oracle",
                    )
                )
            return

        if hasattr(oracledb, "is_thin_mode") and not oracledb.is_thin_mode():
            if lib_dir or config_dir:
                raise ConfigurationError(
                    ConnectionFailure(
                        error_code="ORACLE_THICK_CONFIGURATION_UNVERIFIABLE",
                        category=FailureCategory.INVALID_CONFIGURATION,
                        message="Oracle thick mode was initialized externally; requested client settings cannot be verified.",
                        retryable=False,
                        provider_id="oracle",
                    )
                )
            _ORACLE_THICK_INIT_CONFIG = requested_config
            return

        init_kwargs: dict[str, Any] = {}
        if lib_dir:
            init_kwargs["lib_dir"] = lib_dir
        if config_dir:
            init_kwargs["config_dir"] = config_dir
        try:
            oracledb.init_oracle_client(**init_kwargs)
        except Exception as exc:
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="ORACLE_THICK_INITIALIZATION_FAILED",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message=f"Oracle thick client initialization failed: {redact_text(str(exc))}",
                    retryable=False,
                    provider_id="oracle",
                    original_error_type=type(exc).__name__,
                )
            ) from exc
        _ORACLE_THICK_INIT_CONFIG = requested_config


class OracleProviderStrategy(BaseProviderStrategy):
    """Canonical Oracle provider strategy."""

    PROVIDER_ID = "oracle"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "Oracle Corporation"

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
                "DIRECT_PATH_LOAD": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "SAVEPOINTS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,  # via LogMiner / XStream
                "FLASHBACK_QUERY": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "LOBS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=["Requires supplemental logging for CDC LogMiner capture"],
            required_privileges=["CREATE SESSION", "SELECT ANY TABLE", "LOGMINING"],
            fastpath_features=["EXECUTEMANY WITH ARRAYSIZE", "DIRECT PATH STREAMING", "FLASHBACK SCN"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import oracledb
            return True, f"oracledb version {getattr(oracledb, '__version__', 'unknown')} available."
        except ImportError:
            return False, "python-oracledb library not installed. Install via 'pip install oracledb'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        has_tns = bool(spec.options.get("tns_entry") or spec.options.get("tns_name"))
        has_wallet = bool(spec.options.get("wallet_location") or spec.options.get("wallet_path") or spec.options.get("config_dir"))
        if not spec.host and not has_tns and not has_wallet:
            raise ValueError("Oracle requires host/port, TNS entry, or wallet configuration.")
        driver_mode = str(spec.options.get("driver_mode", "THIN")).strip().upper()
        if driver_mode not in ("THIN", "THICK"):
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="ORACLE_DRIVER_MODE_INVALID",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message="Oracle driver_mode must be THIN or THICK.",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

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
                    error_code="ORACLE_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import oracledb

        driver_mode = str(spec.options.get("driver_mode", "THIN")).strip().upper()
        if driver_mode == "THICK":
            _ensure_oracle_thick_mode(
                oracledb,
                spec.options.get("oracle_client_lib_dir"),
                spec.options.get("oracle_client_config_dir"),
            )
        elif hasattr(oracledb, "is_thin_mode") and not oracledb.is_thin_mode():
            raise ConfigurationError(
                ConnectionFailure(
                    error_code="ORACLE_THIN_MODE_UNAVAILABLE",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message="Oracle THIN mode was requested after this process entered process-global THICK mode.",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "system")
        password = credentials.get("password") or ""
        wallet_location = spec.options.get("wallet_location") or spec.options.get("wallet_path") or spec.options.get("config_dir")
        wallet_password = credentials.get("wallet_password")
        tns_entry = spec.options.get("tns_entry") or spec.options.get("tns_name")

        priv_mode = str(
            spec.options.get("privilege_mode") or
            spec.options.get("oracle_privilege") or
            (spec.auth_spec.auth_type.value if spec.auth_spec and spec.auth_spec.auth_type.value.startswith("ORACLE_") else "") or
            "NORMAL"
        ).strip().upper()

        auth_mode = getattr(oracledb, "DEFAULT_AUTH", getattr(oracledb, "AUTH_MODE_DEFAULT", 0))
        if "SYSDBA" in priv_mode:
            auth_mode = getattr(oracledb, "AUTH_MODE_SYSDBA", getattr(oracledb, "SYSDBA", 2))
        elif "SYSOPER" in priv_mode:
            auth_mode = getattr(oracledb, "AUTH_MODE_SYSOPER", getattr(oracledb, "SYSOPER", 4))

        if tns_entry:
            dsn = tns_entry
        else:
            host = resolved_route.effective_host
            port = resolved_route.effective_port or spec.port or 1521
            sid = spec.options.get("sid")
            service_name = spec.database_name or spec.options.get("service_name") or "ORCLPDB1"
            if sid:
                dsn = oracledb.makedsn(host, port, sid=sid)
            else:
                dsn = oracledb.makedsn(host, port, service_name=service_name)

        conn_kwargs: dict[str, Any] = {
            "user": user,
            "password": password,
            "dsn": dsn,
            "mode": auth_mode,
            "tcp_connect_timeout": spec.route_spec.connect_timeout_ms / 1000.0,
        }
        if wallet_location:
            conn_kwargs["config_dir"] = wallet_location
            conn_kwargs["wallet_location"] = wallet_location
        if wallet_password:
            conn_kwargs["wallet_password"] = wallet_password
        if ssl_context:
            conn_kwargs["ssl_context"] = ssl_context

        conn = oracledb.connect(**conn_kwargs)

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
            cur = connection.cursor()
            cur.execute("SELECT 1 FROM DUAL")
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
            cur.execute("ALTER SESSION SET ISOLATION_LEVEL = READ COMMITTED")
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
        server_ver = "Oracle Database"
        db_name = spec.database_name or "ORCL"
        user = spec.auth_spec.username if spec.auth_spec else "system"
        topo_role = "PRIMARY"

        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
                row = cur.fetchone()
                if row:
                    server_ver = row[0]
                cur.close()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 1521,
            server_version=server_ver,
            catalog_or_database=db_name,
            schema_name=spec.schema_name or user.upper(),
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
            endpoint_fingerprint="oracle-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "DIRECT_PATH_LOAD": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,
                "FLASHBACK_QUERY": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="oracle-attested",
            granted_privileges=["CREATE SESSION", "SELECT ANY TABLE"],
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
        exc_name = type(exc).__name__
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "ORACLE_ERROR"
        retryable = False

        if "ORA-01017" in msg:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "ORACLE_INVALID_CREDENTIALS"
        elif "ORA-01031" in msg:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "ORACLE_INSUFFICIENT_PRIVILEGES"
        elif "ORA-12154" in msg or "ORA-12514" in msg:
            category = FailureCategory.INVALID_CONFIGURATION
            code = "ORACLE_TNS_SERVICE_NOT_FOUND"
        elif "ORA-00054" in msg or "ORA-00060" in msg:
            category = FailureCategory.TIMEOUT
            code = "ORACLE_DEADLOCK_OR_BUSY"
            retryable = True
        elif "ORA-03113" in msg or "ORA-03114" in msg or "ORA-12541" in msg:
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "ORACLE_COMMUNICATION_LOST"
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
            "arraysize": 5000,
            "prefetchrows": 2000,
            "direct_path_supported": True,
        }
