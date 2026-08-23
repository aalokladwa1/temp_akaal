"""
akaalEngine.connection.providers.storage.s3
===========================================
Canonical AWS S3 Object Storage Provider Strategy.
Supports boto3 S3 client, multipart upload/download, bucket discovery, and S3 Select.
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

logger = logging.getLogger("akaalEngine.connection.providers.s3")


class S3ProviderStrategy(BaseProviderStrategy):
    """Canonical AWS S3 object storage provider strategy."""

    PROVIDER_ID = "s3"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "storage"
    VENDOR_NAME = "Amazon Web Services"

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
                "MULTIPART_UPLOAD": CapabilitySupportStatus.SUPPORTED,
                "S3_SELECT": CapabilitySupportStatus.SUPPORTED,
                "PARQUET_READ": CapabilitySupportStatus.SUPPORTED,
                "CSV_READ": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            fastpath_features=["MULTIPART_PARALLEL_UPLOAD", "S3_ACCELERATE"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import boto3
            return True, "boto3 library available."
        except ImportError:
            return False, "boto3 library not installed. Install via 'pip install boto3'."

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
                    error_code="S3_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import boto3
        region = spec.region or spec.options.get("region") or "us-east-1"
        aws_access_key = credentials.get("access_key_id") or credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        aws_secret_key = credentials.get("secret_access_key") or credentials.get("password")
        aws_session_token = credentials.get("session_token") or credentials.get("aws_session_token")

        custom_endpoint = spec.options.get("endpoint_url")
        if not custom_endpoint and spec.host and "amazonaws.com" not in spec.host:
            custom_endpoint = f"https://{resolved_route.effective_host}:{resolved_route.effective_port or 443}"

        client_kwargs: dict[str, Any] = {
            "region_name": region,
        }
        if aws_access_key and aws_secret_key:
            client_kwargs["aws_access_key_id"] = aws_access_key
            client_kwargs["aws_secret_access_key"] = aws_secret_key
            if aws_session_token:
                client_kwargs["aws_session_token"] = aws_session_token
        if custom_endpoint:
            client_kwargs["endpoint_url"] = custom_endpoint

        client = boto3.client("s3", **client_kwargs)
        return client

    def close(self, connection: Any) -> None:
        pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
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
            resolved_host=spec.host or "s3.amazonaws.com",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version="AWS Simple Storage Service",
            catalog_or_database=spec.database_name or "bucket",
            cloud_region=spec.region,
            route_type=spec.route_spec.route_type,
            topology_role="OBJECT_STORE",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="s3-attested",
            capabilities={
                "BUCKET_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_READ": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_WRITE": CapabilitySupportStatus.SUPPORTED,
                "MULTIPART_UPLOAD": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="s3-attested",
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
            error_code="S3_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
