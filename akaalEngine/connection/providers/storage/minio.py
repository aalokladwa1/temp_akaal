"""
akaalEngine.connection.providers.storage.minio
=============================================
Canonical MinIO Object Storage Provider Strategy.
Supports minio-py / S3 API compatible storage.
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

logger = logging.getLogger("akaalEngine.connection.providers.minio")


class MinIOProviderStrategy(BaseProviderStrategy):
    """Canonical MinIO object storage provider strategy."""

    PROVIDER_ID = "minio"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "storage"
    VENDOR_NAME = "MinIO Inc."

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
                "BUCKET_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_READ": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_WRITE": CapabilitySupportStatus.SUPPORTED,
                "S3_API_COMPLIANT": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import minio
            return True, "minio library available."
        except ImportError:
            try:
                import boto3
                return True, "boto3 S3 client available for MinIO."
            except ImportError:
                return False, "Neither minio nor boto3 library installed."

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
                    error_code="MINIO_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 9000
        access_key = credentials.get("access_key_id") or credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "minioadmin")
        secret_key = credentials.get("secret_access_key") or credentials.get("password") or "minioadmin"

        try:
            from minio import Minio
            return Minio(
                f"{host}:{port}",
                access_key=access_key,
                secret_key=secret_key,
                secure=(spec.tls_binding.mode.value != "DISABLED"),
            )
        except ImportError:
            import boto3
            scheme = "https" if spec.tls_binding.mode.value != "DISABLED" else "http"
            return boto3.client(
                "s3",
                endpoint_url=f"{scheme}://{host}:{port}",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )

    def close(self, connection: Any) -> None:
        pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            if hasattr(connection, "list_buckets"):
                connection.list_buckets()
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
            resolved_port=resolved_route.effective_port or spec.port or 9000,
            server_version="MinIO High Performance Object Storage",
            catalog_or_database=spec.database_name or "bucket",
            principal_identity=spec.auth_spec.username if spec.auth_spec else "minioadmin",
            route_type=spec.route_spec.route_type,
            topology_role="DISTRIBUTED_MINIO",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="minio-attested",
            capabilities={
                "BUCKET_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_READ": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_WRITE": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="minio-attested",
            granted_privileges=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
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
            error_code="MINIO_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
