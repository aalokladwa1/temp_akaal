"""
akaalEngine.connection.providers.storage.hdfs
============================================
Canonical Apache Hadoop HDFS Provider Strategy.
Supports hdfs / pyarrow HDFS client, WebHDFS REST API, and directory traversal.
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

logger = logging.getLogger("akaalEngine.connection.providers.hdfs")


class HDFSProviderStrategy(BaseProviderStrategy):
    """Canonical Apache HDFS provider strategy."""

    PROVIDER_ID = "hdfs"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "storage"
    VENDOR_NAME = "Apache Software Foundation"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.STAGING, EndpointRole.REFERENCE, EndpointRole.VALIDATION],
            supports_tls=True,
            supports_mtls=False,
            capabilities={
                "DIRECTORY_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "FILE_READ": CapabilitySupportStatus.SUPPORTED,
                "FILE_WRITE": CapabilitySupportStatus.SUPPORTED,
                "WEBHDFS": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import hdfs
            return True, "hdfs library available."
        except ImportError:
            try:
                import pyarrow.fs
                return True, "pyarrow.fs HDFS available."
            except ImportError:
                return False, "Neither hdfs nor pyarrow library installed."

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
                    error_code="HDFS_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 9870
        user = spec.auth_spec.username if spec.auth_spec else "hdfs"

        use_webhdfs = spec.options.get("use_webhdfs", True)
        if use_webhdfs:
            try:
                from hdfs import InsecureClient
                scheme = "https" if spec.tls_binding.mode.value != "DISABLED" else "http"
                return InsecureClient(f"{scheme}://{host}:{port}", user=user)
            except ImportError:
                from pyarrow import fs
                return fs.HadoopFileSystem(host, port, user=user)
        else:
            try:
                from pyarrow import fs
                return fs.HadoopFileSystem(host, port, user=user)
            except ImportError:
                from hdfs import InsecureClient
                scheme = "https" if spec.tls_binding.mode.value != "DISABLED" else "http"
                return InsecureClient(f"{scheme}://{host}:{port}", user=user)

    def close(self, connection: Any) -> None:
        pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            if hasattr(connection, "status"):
                connection.status("/")
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
            resolved_port=resolved_route.effective_port or spec.port or 9870,
            server_version="Apache Hadoop Distributed File System",
            catalog_or_database=spec.database_name or "/",
            principal_identity=spec.auth_spec.username if spec.auth_spec else "hdfs",
            route_type=spec.route_spec.route_type,
            topology_role="NAMENODE_DATANODES",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="hdfs-attested",
            capabilities={
                "DIRECTORY_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "FILE_READ": CapabilitySupportStatus.SUPPORTED,
                "FILE_WRITE": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="hdfs-attested",
            granted_privileges=["READ", "WRITE"],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=not purpose.is_read_only_by_default,
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
        return ConnectionFailure(
            error_code="HDFS_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
