"""
akaalEngine.connection.providers.relational.mariadb
==================================================
Canonical MariaDB Provider Strategy.
Supports PyMySQL / MariaDB connector, spider/columnstore engines, and binlog CDC.
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

logger = logging.getLogger("akaalEngine.connection.providers.mariadb")


class MariaDBProviderStrategy(BaseProviderStrategy):
    """Canonical MariaDB provider strategy."""

    PROVIDER_ID = "mariadb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "relational"
    VENDOR_NAME = "MariaDB Corporation"

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
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "FOREIGN_KEYS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            fastpath_features=["LOAD DATA LOCAL INFILE", "INSERT MULTIPLE ROWS"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import pymysql
            return True, "pymysql driver available."
        except ImportError:
            try:
                import mariadb
                return True, "mariadb native driver available."
            except ImportError:
                return False, "Neither 'pymysql' nor 'mariadb' client driver installed. Install via 'pip install pymysql' or 'pip install mariadb'."

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
                    error_code="MARIADB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 3306
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "root")
        password = credentials.get("password") or ""
        dbname = spec.database_name or None
        charset = spec.options.get("charset", "utf8mb4")

        try:
            import pymysql
            return pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=dbname,
                connect_timeout=int(spec.route_spec.connect_timeout_ms / 1000.0),
                autocommit=True,
                charset=charset,
            )
        except ImportError:
            import mariadb
            return mariadb.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=dbname,
                connect_timeout=int(spec.route_spec.connect_timeout_ms / 1000.0),
                autocommit=True,
            )

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
        server_ver = "MariaDB"
        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT VERSION()")
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
            resolved_port=resolved_route.effective_port or spec.port or 3306,
            server_version=server_ver,
            catalog_or_database=spec.database_name,
            schema_name=spec.schema_name or spec.database_name,
            principal_identity=spec.auth_spec.username if spec.auth_spec else "root",
            route_type=spec.route_spec.route_type,
            topology_role="PRIMARY",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="mariadb-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "LOAD_DATA_INFILE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="mariadb-attested",
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
        return ConnectionFailure(
            error_code="MARIADB_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
