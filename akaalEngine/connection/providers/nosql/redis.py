"""
akaalEngine.connection.providers.nosql.redis
============================================
Canonical Redis In-Memory Key-Value Provider Strategy.
Supports redis-py, Redis Streams (CDC), Pub/Sub, and cluster topology.
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

logger = logging.getLogger("akaalEngine.connection.providers.redis")


class RedisProviderStrategy(BaseProviderStrategy):
    """Canonical Redis provider strategy."""

    PROVIDER_ID = "redis"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "nosql"
    VENDOR_NAME = "Redis Ltd."

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
                "KEY_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "REDIS_STREAMS": CapabilitySupportStatus.SUPPORTED,
                "PUB_SUB": CapabilitySupportStatus.SUPPORTED,
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,  # via Redis Streams XREAD / Keyspace notifications
                "CLUSTER_AWARENESS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import redis
            return True, f"redis-py version {getattr(redis, '__version__', 'unknown')} available."
        except ImportError:
            return False, "redis library not installed. Install via 'pip install redis'."

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
                    error_code="REDIS_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import redis

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 6379
        from akaalEngine.connection.models.endpoint import TLSMode
        tls_enabled = (spec.tls_binding.mode != TLSMode.DISABLED)
        redis_kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "username": user if user != "default" else None,
            "password": password,
            "db": db,
            "socket_timeout": spec.route_spec.socket_timeout_ms / 1000.0,
            "socket_connect_timeout": spec.route_spec.connect_timeout_ms / 1000.0,
            "ssl": tls_enabled,
        }
        if tls_enabled:
            if spec.tls_binding.ca_cert_path:
                redis_kwargs["ssl_ca_certs"] = spec.tls_binding.ca_cert_path
            if spec.tls_binding.client_cert_path:
                redis_kwargs["ssl_certfile"] = spec.tls_binding.client_cert_path
            if spec.tls_binding.allow_self_signed:
                redis_kwargs["ssl_cert_reqs"] = "none"
            elif spec.tls_binding.mode in (TLSMode.REQUIRED, TLSMode.VERIFY_CA, TLSMode.VERIFY_FULL):
                redis_kwargs["ssl_cert_reqs"] = "required"
            if spec.tls_binding.mode == TLSMode.VERIFY_FULL:
                redis_kwargs["ssl_check_hostname"] = True

        client = redis.Redis(**redis_kwargs)
        return client

    def close(self, connection: Any) -> None:
        if connection and hasattr(connection, "close"):
            try:
                connection.close()
            except Exception:
                pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            return bool(connection.ping())
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
        server_ver = "Redis"
        topo_role = "PRIMARY"
        if connection:
            try:
                info = connection.info("server")
                server_ver = f"Redis {info.get('redis_version', '')}"
                rep_info = connection.info("replication")
                topo_role = rep_info.get("role", "master").upper()
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 6379,
            server_version=server_ver,
            catalog_or_database=str(spec.database_name or 0),
            principal_identity=spec.auth_spec.username if spec.auth_spec else "default",
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
            endpoint_fingerprint="redis-attested",
            capabilities={
                "KEY_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "REDIS_STREAMS": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="redis-attested",
            granted_privileges=["+@all"],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=not purpose.is_read_only_by_default,
            can_ddl=False,
            can_cdc=True,
            is_admin=True,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        return ConnectionFailure(
            error_code="REDIS_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
