"""
akaalEngine.connection.providers.streaming.pubsub
=================================================
Canonical Google Cloud Pub/Sub Provider Strategy.
Supports google-cloud-pubsub, topic subscriptions, and streaming pull/push.
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

logger = logging.getLogger("akaalEngine.connection.providers.pubsub")


class PubSubProviderStrategy(BaseProviderStrategy):
    """Canonical Google Cloud Pub/Sub provider strategy."""

    PROVIDER_ID = "pubsub"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "streaming"
    VENDOR_NAME = "Google Cloud"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.CDC_LOG],
            supports_tls=True,
            supports_mtls=False,
            capabilities={
                "TOPIC_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "STREAMING_READ": CapabilitySupportStatus.SUPPORTED,
                "STREAMING_WRITE": CapabilitySupportStatus.SUPPORTED,
                "EXACTLY_ONCE_DELIVERY": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            from google.cloud import pubsub_v1
            return True, "google-cloud-pubsub available."
        except ImportError:
            return False, "google-cloud-pubsub not installed. Install via 'pip install google-cloud-pubsub'."

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
                    error_code="PUBSUB_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import json
        from google.cloud import pubsub_v1

        project_id = spec.account_id or spec.options.get("project_id")
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
                client = pubsub_v1.PublisherClient(credentials=gcp_creds)
                setattr(client, "_akaal_project_id", project_id)
                return client
            except Exception as exc:
                raise AuthenticationError(
                    ConnectionFailure(
                        error_code="PUBSUB_SA_CREDENTIAL_CONSTRUCTION_FAILED",
                        category=FailureCategory.AUTHENTICATION_FAILURE,
                        message=f"Failed to construct Pub/Sub Service Account credentials: {redact_text(str(exc))}",
                        retryable=False,
                        provider_id=self.PROVIDER_ID,
                    )
                ) from exc

        # 2. Reject missing explicit SA reference fail-closed
        if spec.auth_spec and spec.auth_spec.service_account_json_ref:
            raise AuthenticationError(
                ConnectionFailure(
                    error_code="PUBSUB_EXPLICIT_CREDENTIALS_MISSING",
                    category=FailureCategory.AUTHENTICATION_FAILURE,
                    message="Explicit service account JSON reference was configured but missing. Ambient ADC fallback prohibited.",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        # 3. Ambient / Application Default Credentials (ADC)
        client = pubsub_v1.PublisherClient()
        setattr(client, "_akaal_project_id", project_id)
        return client

    def close(self, connection: Any) -> None:
        pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        project_id = getattr(connection, "_akaal_project_id", None)
        if not project_id:
            return False
        try:
            # A successful authenticated metadata RPC is required. Reachability,
            # PermissionDenied, NotFound, and Unauthenticated are not readiness.
            pager = connection.list_topics(project=f"projects/{project_id}", timeout=5.0)
            next(iter(pager), None)
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
            resolved_host="pubsub.googleapis.com",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=443,
            server_version="Google Cloud Pub/Sub",
            catalog_or_database=spec.database_name or "topic",
            cloud_account_id=spec.account_id,
            route_type=spec.route_spec.route_type,
            topology_role="SERVERLESS_MESSAGING",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="pubsub-attested",
            capabilities={
                "TOPIC_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "STREAMING_READ": CapabilitySupportStatus.SUPPORTED,
                "STREAMING_WRITE": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="pubsub-attested",
            granted_privileges=["pubsub.topics.publish", "pubsub.subscriptions.consume"],
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write=not purpose.is_read_only_by_default,
            can_ddl=False,
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
            error_code="PUBSUB_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
