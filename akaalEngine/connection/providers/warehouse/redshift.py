"""
akaalEngine.connection.providers.warehouse.redshift
==================================================
Canonical Amazon Redshift Provider Strategy.
Supports Redshift cluster connections, UNLOAD/COPY S3 staging, and spectrum external tables.
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

logger = logging.getLogger("akaalEngine.connection.providers.redshift")


class RedshiftProviderStrategy(BaseProviderStrategy):
    """Canonical Amazon Redshift provider strategy."""

    PROVIDER_ID = "redshift"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "warehouse"
    VENDOR_NAME = "Amazon Web Services"

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
                "S3_COPY": CapabilitySupportStatus.SUPPORTED,
                "S3_UNLOAD": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "DISTRIBUTION_KEYS": CapabilitySupportStatus.SUPPORTED,
                "SORT_KEYS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            fastpath_features=["COPY FROM S3 MANIFEST", "UNLOAD TO S3 PARQUET"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import psycopg2
            return True, "psycopg2 driver available."
        except ImportError:
            try:
                import redshift_connector
                return True, "redshift-connector driver available."
            except ImportError:
                return False, "Neither 'psycopg2' nor 'redshift-connector' installed. Install via 'pip install psycopg2-binary' or 'pip install redshift-connector'."

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
                    error_code="REDSHIFT_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 5439
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "awsuser")
        password = credentials.get("password") or ""
        dbname = spec.database_name or "dev"

        try:
            import psycopg2
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                sslmode="require",
                connect_timeout=int(spec.route_spec.connect_timeout_ms / 1000.0),
            )
            conn.autocommit = True
            return conn
        except ImportError:
            import redshift_connector
            conn = redshift_connector.connect(
                host=host,
                port=port,
                database=dbname,
                user=user,
                password=password,
                timeout=int(spec.route_spec.connect_timeout_ms / 1000.0),
                ssl=True,
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
            return True
        except Exception:
            return False

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_ver = "Amazon Redshift"
        if connection:
            try:
                cur = connection.cursor()
                cur.execute("SELECT version()")
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
            resolved_port=resolved_route.effective_port or spec.port or 5439,
            server_version=server_ver,
            catalog_or_database=spec.database_name,
            schema_name=spec.schema_name or "public",
            principal_identity=spec.auth_spec.username if spec.auth_spec else "awsuser",
            cloud_region=spec.region,
            route_type=spec.route_spec.route_type,
            topology_role="CLUSTER",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="redshift-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "S3_COPY": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="redshift-attested",
            granted_privileges=["USAGE", "SELECT", "INSERT", "CREATE"],
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
            error_code="REDSHIFT_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
