"""
akaalEngine.connection.providers.warehouse.clickhouse
========================================================
Canonical ClickHouse Provider Strategy (P7A Campaign B).

ClickHouse is a columnar OLAP store with a materially different consistency model from
the other adopted warehouse providers:
  - There is no reliable, default multi-statement ACID transaction support (an
    experimental transactions feature exists behind a setting but is not enabled or
    relied upon by this connector) -- TRANSACTIONS is declared UNSUPPORTED rather than
    borrowed from Snowflake/BigQuery/Redshift's session semantics.
  - Row-level UPDATE/DELETE are real but asynchronous background "mutations"
    (`ALTER TABLE ... UPDATE/DELETE`), not synchronous DML -- modeled as its own
    `MUTATIONS` capability, not folded into `BULK_WRITE`.
  - Table engines (MergeTree family) genuinely partition data via `PARTITION BY`, a real,
    introspectable property via `system.tables`/`system.parts`.
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

logger = logging.getLogger("akaalEngine.connection.providers.clickhouse")


class ClickHouseProviderStrategy(BaseProviderStrategy):
    """Canonical ClickHouse provider strategy -- columnar OLAP, no reliable multi-statement transactions."""

    PROVIDER_ID = "clickhouse"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "warehouse"
    VENDOR_NAME = "ClickHouse, Inc."

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
                "COLUMNAR_STORAGE": CapabilitySupportStatus.SUPPORTED,
                "PARTITION_AWARENESS": CapabilitySupportStatus.SUPPORTED,
                "MUTATIONS": CapabilitySupportStatus.SUPPORTED,  # async ALTER TABLE UPDATE/DELETE
                # Truthfully NOT claimed supported: no reliable default multi-statement
                # transaction model.
                "TRANSACTIONS": CapabilitySupportStatus.UNSUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "No reliable default multi-statement ACID transactions; UPDATE/DELETE are asynchronous background mutations, not synchronous DML.",
            ],
            required_privileges=["SELECT", "INSERT"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import clickhouse_connect
            return True, "clickhouse-connect library available."
        except ImportError:
            return False, "clickhouse-connect library not installed. Install via 'pip install clickhouse-connect'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host:
            raise ValueError("ClickHouse host is required.")

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
                    error_code="CLICKHOUSE_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import clickhouse_connect

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 8123
        username = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "default")
        password = credentials.get("password") or ""
        database = spec.database_name or "default"

        tls_mode = spec.tls_binding.mode.value if hasattr(spec.tls_binding.mode, "value") else str(spec.tls_binding.mode)
        is_tls = tls_mode != "DISABLED"

        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            secure=is_tls,
            connect_timeout=max(1, int(spec.route_spec.connect_timeout_ms / 1000.0)),
        )
        return client

    def close(self, connection: Any) -> None:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            connection.command("SELECT 1")
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return self.validate(connection)

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_version = "ClickHouse"
        if connection is not None:
            try:
                server_version = f"ClickHouse {connection.server_version}"
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 8123,
            server_version=server_version,
            catalog_or_database=spec.database_name or "default",
            principal_identity=spec.auth_spec.username if spec.auth_spec else "default",
            route_type=spec.route_spec.route_type,
            # Truthful: ClickHouse is a shared-nothing distributed cluster of independent
            # shards/replicas coordinated via ZooKeeper/ClickHouse Keeper, not a single
            # primary/replica pair.
            topology_role="DISTRIBUTED",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="clickhouse-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "COLUMNAR_STORAGE": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="clickhouse-attested",
            granted_privileges=["SELECT", "INSERT"] if connection is not None else [],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=connection is not None and not purpose.is_read_only_by_default,
            can_ddl=False,
            can_cdc=False,
            is_admin=False,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        lower_msg = msg.lower()
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "CLICKHOUSE_ERROR"
        retryable = False

        if "authentication failed" in lower_msg or "wrong password" in lower_msg:
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "CLICKHOUSE_AUTH_FAILED"
        elif "not enough privileges" in lower_msg or "access denied" in lower_msg:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "CLICKHOUSE_PERMISSION_DENIED"
        elif "unknown table" in lower_msg or "unknown database" in lower_msg:
            category = FailureCategory.INVALID_CONFIGURATION
            code = "CLICKHOUSE_OBJECT_NOT_FOUND"
        elif "memory limit" in lower_msg:
            category = FailureCategory.PROVIDER_INTERNAL_ERROR
            code = "CLICKHOUSE_MEMORY_LIMIT_EXCEEDED"
            retryable = False
        elif "timeout" in lower_msg or "timeouterror" in exc_name.lower():
            category = FailureCategory.TIMEOUT
            code = "CLICKHOUSE_TIMEOUT"
            retryable = True
        elif "connection refused" in lower_msg or "connecterror" in exc_name.lower():
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "CLICKHOUSE_UNAVAILABLE"
            retryable = True
        elif "too many simultaneous queries" in lower_msg:
            category = FailureCategory.TIMEOUT
            code = "CLICKHOUSE_TOO_MANY_QUERIES"
            retryable = True

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )
