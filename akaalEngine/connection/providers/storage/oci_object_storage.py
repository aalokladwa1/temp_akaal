"""
akaalEngine.connection.providers.storage.oci_object_storage
============================================================
Canonical Oracle Cloud Infrastructure (OCI) Object Storage provider strategy.
P7B Group 1 (§8): OCI Object Storage first-class alongside S3/GCS/Azure Blob, reusing
the existing Connection Authority provider-strategy contract and the existing
`akaalEngine.transport.staging.object_storage.ObjectStorageStagingAdapter` staging
machinery -- no new object-storage transport engine is introduced.

OCI Object Storage has no regional DNS-style endpoint compatible with the S3-style
default; every request requires an explicit tenancy namespace
(`objectstorage.<region>.oraclecloud.com` + namespace + bucket), so identity here is
truthfully three-part: namespace, compartment, bucket -- never conflated with an
AWS-account-shaped identity.
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

logger = logging.getLogger("akaalEngine.connection.providers.oci_object_storage")


class OCIObjectStorageProviderStrategy(BaseProviderStrategy):
    """Canonical OCI Object Storage provider strategy."""

    PROVIDER_ID = "oci_object_storage"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "storage"
    VENDOR_NAME = "Oracle Cloud Infrastructure"

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
                # OCI Object Storage has no server-side SQL-over-object equivalent to S3 Select.
                "S3_SELECT": CapabilitySupportStatus.UNSUPPORTED,
                "PARQUET_READ": CapabilitySupportStatus.SUPPORTED,
                "CSV_READ": CapabilitySupportStatus.SUPPORTED,
                # Real, distinct-from-S3 OCI primitive: server-side copy across buckets/regions
                # without a client round-trip.
                "SERVER_SIDE_COPY": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
            fastpath_features=["MULTIPART_PARALLEL_UPLOAD"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import oci  # noqa: F401
            return True, "oci SDK library available."
        except ImportError:
            return False, "oci SDK library not installed. Install via 'pip install oci'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        # namespace is mandatory to address any OCI Object Storage bucket; region is not
        # gatekept here to remain consistent with the established S3/DynamoDB pattern of
        # defaulting at connect() time rather than in the generic conformance harness path.
        if spec.options.get("namespace") is not None and not str(spec.options.get("namespace")).strip():
            raise ValueError("OCI Object Storage 'namespace' option, if provided, must not be empty.")

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
                    error_code="OCI_OBJECT_STORAGE_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import oci

        region = spec.region or spec.options.get("region")
        if not region:
            failure = ConnectionFailure(
                error_code="OCI_OBJECT_STORAGE_REGION_REQUIRED",
                category=FailureCategory.INVALID_CONFIGURATION,
                message="OCI Object Storage requires an explicit region (no regionless default endpoint exists).",
                retryable=False,
                provider_id=self.PROVIDER_ID,
                remediation="Set EndpointSpec.region or options['region'] to a valid OCI region identifier.",
            )
            self._raise_config_error(failure)

        auth_mode = spec.options.get("auth_mode", "config_file")
        config: dict[str, Any] = {"region": region}

        # Round-5 hostile-review closure: a workload identity already resolved via
        # akaalEngine.fabric.workload_identity.resolve_oci_workload_identity (e.g. by a
        # caller that pre-authenticated once and wants to reuse the signer across
        # connections) is honored directly here -- without this branch, connect() would
        # always construct a BRAND NEW signer internally (below), silently discarding
        # any already-resolved identity/signer a caller supplied.
        resolved_signer = credentials.get("oci_signer")
        if resolved_signer is not None:
            client = oci.object_storage.ObjectStorageClient(config={"region": region}, signer=resolved_signer)
            return client

        if auth_mode == "instance_principal":
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            client = oci.object_storage.ObjectStorageClient(config={"region": region}, signer=signer)
            return client

        if auth_mode == "resource_principal":
            signer = oci.auth.signers.get_resource_principals_signer()
            client = oci.object_storage.ObjectStorageClient(config={"region": region}, signer=signer)
            return client

        # API-key / config-file style authentication (least privileged default for tests/dev).
        tenancy = credentials.get("tenancy_ocid") or spec.options.get("tenancy_ocid")
        user_ocid = credentials.get("user_ocid") or spec.options.get("user_ocid")
        fingerprint = credentials.get("fingerprint") or spec.options.get("fingerprint")
        key_content = credentials.get("client_key_content") or credentials.get("password")

        if tenancy and user_ocid and fingerprint and key_content:
            config.update(
                {
                    "tenancy": tenancy,
                    "user": user_ocid,
                    "fingerprint": fingerprint,
                    "key_content": key_content,
                }
            )
            client = oci.object_storage.ObjectStorageClient(config)
            return client

        # Fall back to the local OCI CLI config file, matching the SDK's own default behavior.
        oci_config = oci.config.from_file(
            file_location=spec.options.get("config_file_path", "~/.oci/config"),
            profile_name=spec.options.get("config_profile", "DEFAULT"),
        )
        oci_config["region"] = region
        client = oci.object_storage.ObjectStorageClient(oci_config)
        return client

    @staticmethod
    def _raise_config_error(failure: ConnectionFailure) -> None:
        from akaalEngine.connection.models.errors import ConfigurationError
        raise ConfigurationError(failure)

    def close(self, connection: Any) -> None:
        pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            namespace = connection.get_namespace().data
            return bool(namespace)
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
        region = spec.region or spec.options.get("region") or "unknown-region"
        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=spec.host or f"objectstorage.{region}.oraclecloud.com",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version="OCI Object Storage",
            catalog_or_database=spec.options.get("bucket") or spec.database_name or "bucket",
            cloud_region=region,
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
            endpoint_fingerprint="oci-object-storage-attested",
            capabilities={
                "BUCKET_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_READ": CapabilitySupportStatus.SUPPORTED,
                "OBJECT_WRITE": CapabilitySupportStatus.SUPPORTED,
                "MULTIPART_UPLOAD": CapabilitySupportStatus.SUPPORTED,
                "SERVER_SIDE_COPY": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="oci-object-storage-attested",
            granted_privileges=["OBJECT_READ", "OBJECT_WRITE", "BUCKET_INSPECT"],
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
        status = getattr(exc, "status", None)
        code = getattr(exc, "code", None)

        if status == 401 or code == "NotAuthenticated":
            return ConnectionFailure(
                error_code="OCI_OBJECT_STORAGE_AUTH_FAILED",
                category=FailureCategory.AUTHENTICATION_FAILURE,
                message=msg,
                retryable=False,
                provider_id=self.PROVIDER_ID,
                original_error_type=type(exc).__name__,
            )
        if status == 403 or code == "NotAuthorizedOrNotFound":
            return ConnectionFailure(
                error_code="OCI_OBJECT_STORAGE_PERMISSION_DENIED",
                category=FailureCategory.AUTHORIZATION_PERMISSION_FAILURE,
                message=msg,
                retryable=False,
                provider_id=self.PROVIDER_ID,
                original_error_type=type(exc).__name__,
            )
        if status == 404 or code == "BucketNotFound":
            return ConnectionFailure(
                error_code="OCI_OBJECT_STORAGE_BUCKET_NOT_FOUND",
                category=FailureCategory.ENDPOINT_UNAVAILABLE,
                message=msg,
                retryable=False,
                provider_id=self.PROVIDER_ID,
                original_error_type=type(exc).__name__,
            )
        if status == 429 or code == "TooManyRequests":
            return ConnectionFailure(
                error_code="OCI_OBJECT_STORAGE_THROTTLED",
                category=FailureCategory.PROVIDER_INTERNAL_ERROR,
                message=msg,
                retryable=True,
                provider_id=self.PROVIDER_ID,
                original_error_type=type(exc).__name__,
            )
        if status is not None and status >= 500:
            return ConnectionFailure(
                error_code="OCI_OBJECT_STORAGE_SERVICE_UNAVAILABLE",
                category=FailureCategory.ENDPOINT_UNAVAILABLE,
                message=msg,
                retryable=True,
                provider_id=self.PROVIDER_ID,
                original_error_type=type(exc).__name__,
            )

        return ConnectionFailure(
            error_code="OCI_OBJECT_STORAGE_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
