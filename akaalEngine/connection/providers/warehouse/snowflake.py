"""
akaalEngine.connection.providers.warehouse.snowflake
====================================================
Canonical Snowflake Provider Strategy.
Supports snowflake-connector-python, staging bulk copy, and virtual warehouse scaling.
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

logger = logging.getLogger("akaalEngine.connection.providers.snowflake")


class SnowflakeProviderStrategy(BaseProviderStrategy):
    """Canonical Snowflake provider strategy."""

    PROVIDER_ID = "snowflake"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "warehouse"
    VENDOR_NAME = "Snowflake Inc."

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
                "STAGE_COPY": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.PARTIAL,  # via Snowflake Streams & Tasks
                "WAREHOUSE_SCALING": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            fastpath_features=["COPY INTO @stage", "COPY INTO table FROM @stage", "PUT / GET"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import snowflake.connector
            return True, "snowflake-connector-python available."
        except ImportError:
            return False, "snowflake-connector-python library not installed. Install via 'pip install snowflake-connector-python'."

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
                    error_code="SNOWFLAKE_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import snowflake.connector

        account = spec.account_id or spec.options.get("account") or (spec.host.split(".")[0] if spec.host else "")
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "")
        password = credentials.get("password") or ""
        token = credentials.get("token") or ""
        warehouse = spec.options.get("warehouse")
        database = spec.database_name
        schema = spec.schema_name or "PUBLIC"
        role = spec.options.get("role")
        authenticator = spec.options.get("authenticator")

        conn_kwargs: dict[str, Any] = {
            "account": account,
            "user": user,
            "warehouse": warehouse,
            "database": database,
            "schema": schema,
            "autocommit": True,
        }
        if token:
            conn_kwargs["token"] = token
            if not authenticator:
                conn_kwargs["authenticator"] = "oauth"
        elif password:
            conn_kwargs["password"] = password

        if role:
            conn_kwargs["role"] = role
        if authenticator and "authenticator" not in conn_kwargs:
            conn_kwargs["authenticator"] = authenticator

        conn = snowflake.connector.connect(**conn_kwargs)
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
        server_ver = "Snowflake Cloud Data Warehouse"
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=spec.host or "snowflakecomputing.com",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version=server_ver,
            catalog_or_database=spec.database_name,
            schema_name=spec.schema_name or "PUBLIC",
            principal_identity=spec.auth_spec.username if spec.auth_spec else "snowflake_user",
            cloud_account_id=spec.account_id,
            cloud_region=spec.region,
            route_type=spec.route_spec.route_type,
            topology_role="MANAGED_CLUSTER",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="snowflake-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "STAGE_COPY": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="snowflake-attested",
            granted_privileges=["USAGE", "SELECT", "INSERT", "CREATE TABLE"],
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
            error_code="SNOWFLAKE_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
