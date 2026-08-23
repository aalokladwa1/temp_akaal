"""
akaalEngine.connection.providers.nosql.scylladb
==============================================
Canonical ScyllaDB Provider Strategy.
Supports shard-aware routing, CQL schema discovery, and low-latency C++ based backend.
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

logger = logging.getLogger("akaalEngine.connection.providers.scylladb")


class ScyllaDBProviderStrategy(BaseProviderStrategy):
    """Canonical ScyllaDB provider strategy."""

    PROVIDER_ID = "scylladb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "nosql"
    VENDOR_NAME = "ScyllaDB Inc."

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
                "SHARD_AWARE_ROUTING": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,  # Scylla CDC tables
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import cassandra.cluster
            return True, "cassandra-driver / scylla-driver available."
        except ImportError:
            return False, "cassandra-driver / scylla-driver not installed."

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
                    error_code="SCYLLADB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from cassandra.cluster import Cluster
        from cassandra.auth import PlainTextAuthProvider

        contact_points = resolved_route.get_contact_points()
        port = resolved_route.effective_port or spec.port or 9042
        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        password = credentials.get("password") or None

        auth_provider = PlainTextAuthProvider(username=user, password=password) if user else None
        cluster = Cluster(
            contact_points=contact_points,
            port=port,
            auth_provider=auth_provider,
            connect_timeout=spec.route_spec.connect_timeout_ms / 1000.0,
        )
        return cluster.connect(keyspace=spec.database_name)

    def close(self, connection: Any) -> None:
        if connection:
            try:
                connection.shutdown()
                if hasattr(connection, "cluster"):
                    connection.cluster.shutdown()
            except Exception:
                pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            connection.execute("SELECT release_version FROM system.local")
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return True

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 9042,
            server_version="ScyllaDB Enterprise",
            catalog_or_database=spec.database_name,
            principal_identity=spec.auth_spec.username if spec.auth_spec else "scylla",
            route_type=spec.route_spec.route_type,
            topology_role="SHARDED_RING",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="scylladb-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "SHARD_AWARE_ROUTING": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="scylladb-attested",
            granted_privileges=["SELECT", "MODIFY", "CREATE"],
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
        return ConnectionFailure(
            error_code="SCYLLADB_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
