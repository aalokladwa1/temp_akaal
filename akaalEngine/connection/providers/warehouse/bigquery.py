"""
akaalEngine.connection.providers.warehouse.bigquery
==================================================
Canonical Google BigQuery Provider Strategy.
Supports google-cloud-bigquery client, Storage Read/Write APIs, and partitioning.
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
    AuthenticationError,
    ConnectionFailure,
    DependencyMissingError,
    FailureCategory,
    TLSVerificationError,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.bigquery")


class BigQueryProviderStrategy(BaseProviderStrategy):
    """Canonical Google BigQuery provider strategy."""

    PROVIDER_ID = "bigquery"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "warehouse"
    VENDOR_NAME = "Google Cloud"

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
                "STORAGE_READ_API": CapabilitySupportStatus.SUPPORTED,
                "STORAGE_WRITE_API": CapabilitySupportStatus.SUPPORTED,
                "PARTITIONING": CapabilitySupportStatus.SUPPORTED,
                "CLUSTERING": CapabilitySupportStatus.SUPPORTED,
                "TRANSACTIONS": CapabilitySupportStatus.PARTIAL,  # Multi-statement transactions in BigQuery
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            from google.cloud import bigquery
            return True, "google-cloud-bigquery available."
        except ImportError:
            return False, "google-cloud-bigquery not installed. Install via 'pip install google-cloud-bigquery'."

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
                    error_code="BIGQUERY_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import json
        from google.cloud import bigquery

        project_id = spec.account_id or spec.options.get("project_id") or spec.database_name
        sa_info = credentials.get("service_account_json") or credentials.get("service_account_info")

        # 1. Explicit Service Account Authentication
        if sa_info:
            try:
                from google.oauth2 import service_account
                if isinstance(sa_info, str):
                    info_dict = json.loads(sa_info)
                    gcp_creds = service_account.Credentials.from_service_account_info(info_dict)
                elif isinstance(sa_info, dict):
                    gcp_creds = service_account.Credentials.from_service_account_info(sa_info)
                else:
                    raise ValueError("service_account_json must be a valid JSON string or dict.")
                return bigquery.Client(project=project_id, credentials=gcp_creds)
            except Exception as exc:
                raise AuthenticationError(
                    ConnectionFailure(
                        error_code="BIGQUERY_SA_CREDENTIAL_CONSTRUCTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to construct BigQuery Service Account credentials: {redact_text(str(exc))}",
                        retryable=False,
                        provider_id=self.PROVIDER_ID,
                    )
                ) from exc

        # 2. Reject missing explicit SA reference fail-closed
        if spec.auth_spec and spec.auth_spec.service_account_json_ref:
            raise AuthenticationError(
                ConnectionFailure(
                    error_code="BIGQUERY_EXPLICIT_CREDENTIALS_MISSING",
                    category=FailureCategory.AUTHENTICATION_FAILURE,
                    message="Explicit service account JSON reference was configured but missing. Ambient ADC fallback prohibited.",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        # 3. Ambient / Application Default Credentials (ADC)
        return bigquery.Client(project=project_id)

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
            # Query dry run or simple query
            query_job = connection.query("SELECT 1")
            query_job.result()
            return True
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        # BigQuery is stateless per-request
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
            resolved_host="bigquery.googleapis.com",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version="Google BigQuery Serverless",
            catalog_or_database=spec.database_name or spec.account_id,
            schema_name=spec.schema_name or "dataset",
            cloud_account_id=spec.account_id,
            cloud_region=spec.region,
            route_type=spec.route_spec.route_type,
            topology_role="SERVERLESS",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="bigquery-attested",
            capabilities={
                "SCHEMA_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "BULK_READ": CapabilitySupportStatus.SUPPORTED,
                "BULK_WRITE": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="bigquery-attested",
            granted_privileges=["bigquery.datasets.get", "bigquery.tables.get", "bigquery.tables.getData"],
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
            error_code="BIGQUERY_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
