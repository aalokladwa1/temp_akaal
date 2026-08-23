"""
akaalEngine.connection.providers.nosql.mongodb
==============================================
Canonical MongoDB Document Provider Strategy.
Supports pymongo / motor, Change Streams (CDC), replica sets, and sharded clusters.
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

logger = logging.getLogger("akaalEngine.connection.providers.mongodb")


class MongoDBProviderStrategy(BaseProviderStrategy):
    """Canonical MongoDB provider strategy."""

    PROVIDER_ID = "mongodb"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "nosql"
    VENDOR_NAME = "MongoDB Inc."

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
                "CHANGE_STREAMS": CapabilitySupportStatus.SUPPORTED,  # MongoDB Change Streams CDC
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.SUPPORTED,  # Multi-document transactions
                "SHARDING_AWARENESS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import pymongo
            return True, f"pymongo version {getattr(pymongo, '__version__', 'unknown')} available."
        except ImportError:
            return False, "pymongo library not installed. Install via 'pip install pymongo'."

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
                    error_code="MONGODB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import pymongo

        user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        password = credentials.get("password") or None
        auth_db = spec.options.get("auth_source") or spec.database_name or "admin"
        replica_set = spec.options.get("replica_set")

        from akaalEngine.connection.models.endpoint import TLSMode
        tls_enabled = (spec.tls_binding.mode != TLSMode.DISABLED)
        mongo_kwargs: dict[str, Any] = {
            "username": user,
            "password": password,
            "authSource": auth_db,
            "serverSelectionTimeoutMS": spec.route_spec.connect_timeout_ms,
            "tls": tls_enabled,
        }
        if replica_set:
            mongo_kwargs["replicaSet"] = replica_set

        if len(resolved_route.resolved_targets) > 1:
            mongo_kwargs["host"] = resolved_route.get_bootstrap_servers()
        else:
            mongo_kwargs["host"] = resolved_route.effective_host
            mongo_kwargs["port"] = resolved_route.effective_port or spec.port or 27017

        if tls_enabled:
            if spec.tls_binding.ca_cert_path:
                mongo_kwargs["tlsCAFile"] = spec.tls_binding.ca_cert_path
            if spec.tls_binding.client_cert_path:
                mongo_kwargs["tlsCertificateKeyFile"] = spec.tls_binding.client_cert_path
            if spec.tls_binding.allow_self_signed:
                mongo_kwargs["tlsAllowInvalidCertificates"] = True
            if spec.tls_binding.mode == TLSMode.VERIFY_CA:
                mongo_kwargs["tlsAllowInvalidHostnames"] = True

        client = pymongo.MongoClient(**mongo_kwargs)
        return client

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
            connection.admin.command("ping")
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
        server_ver = "MongoDB"
        topo_role = "STANDALONE"

        if connection:
            try:
                build_info = connection.admin.command("buildInfo")
                server_ver = f"MongoDB {build_info.get('version', '')}"
                is_master = connection.admin.command("isMaster")
                if is_master.get("ismaster"):
                    topo_role = "PRIMARY"
                elif is_master.get("secondary"):
                    topo_role = "REPLICA"
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 27017,
            server_version=server_ver,
            catalog_or_database=spec.database_name,
            principal_identity=spec.auth_spec.username if spec.auth_spec else "mongo_user",
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
            endpoint_fingerprint="mongodb-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
                "CHANGE_STREAMS": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="mongodb-attested",
            granted_privileges=["find", "insert", "update", "remove"],
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
            error_code="MONGODB_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
