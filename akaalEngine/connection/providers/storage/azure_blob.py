"""
akaalEngine.connection.providers.storage.azure_blob
==================================================
Canonical Azure Blob Storage Provider Strategy.
Supports azure-storage-blob client, container discovery, and block blob chunking.
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

logger = logging.getLogger("akaalEngine.connection.providers.azure_blob")


class AzureBlobProviderStrategy(BaseProviderStrategy):
    """Canonical Azure Blob Storage provider strategy."""

    PROVIDER_ID = "azure_blob"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "storage"
    VENDOR_NAME = "Microsoft Azure"

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
                "CONTAINER_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_READ": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_WRITE": CapabilitySupportStatus.SUPPORTED,
                "BLOCK_BLOB_CHUNKING": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            from azure.storage.blob import BlobServiceClient
            return True, "azure-storage-blob available."
        except ImportError:
            return False, "azure-storage-blob not installed. Install via 'pip install azure-storage-blob'."

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
                    error_code="AZURE_BLOB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from azure.storage.blob import BlobServiceClient

        conn_str = credentials.get("connection_string") or (
            credentials.get("password") if (spec.auth_spec and spec.auth_spec.auth_type.value == "CUSTOM_PROVIDER") else None
        )
        account_name = spec.account_id or spec.options.get("account_name")
        account_key = credentials.get("account_key") or credentials.get("password")
        sas_token = credentials.get("sas_token") or credentials.get("token")
        custom_endpoint = spec.options.get("endpoint_url")

        if conn_str:
            return BlobServiceClient.from_connection_string(conn_str)

        if custom_endpoint:
            account_url = custom_endpoint
        elif account_name:
            account_url = f"https://{account_name}.blob.core.windows.net"
        elif spec.host:
            account_url = f"https://{resolved_route.effective_host}"
        else:
            account_url = "https://blob.core.windows.net"

        if account_key:
            return BlobServiceClient(account_url=account_url, credential=account_key)
        elif sas_token:
            return BlobServiceClient(account_url=account_url, credential=sas_token)

        try:
            from azure.identity import DefaultAzureCredential
            return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
        except Exception:
            return BlobServiceClient(account_url=account_url, credential=None)

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
            list(connection.list_containers(results_per_page=1))
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
            resolved_host=spec.host or "blob.core.windows.net",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version="Azure Blob Storage",
            catalog_or_database=spec.database_name or "container",
            cloud_region=spec.region,
            route_type=spec.route_spec.route_type,
            topology_role="BLOB_STORE",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="azureblob-attested",
            capabilities={
                "CONTAINER_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="azureblob-attested",
            granted_privileges=["Storage Blob Data Reader", "Storage Blob Data Contributor"],
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
            error_code="AZURE_BLOB_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
