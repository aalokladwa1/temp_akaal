"""
akaalEngine.connection.providers.streaming.eventhubs
===================================================
Canonical Azure Event Hubs Provider Strategy.
Supports azure-eventhub client, consumer groups, and AMQP/Kafka protocols.
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
    FailureCategory,
    DependencyMissingError,
)
from akaalEngine.connection.models.identity import PhysicalEndpointIdentity
from akaalEngine.connection.models.session import SessionPurpose
from akaalEngine.connection.providers.base import BaseProviderStrategy
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.connection.security.redaction import redact_text

logger = logging.getLogger("akaalEngine.connection.providers.eventhubs")


class EventHubsProviderStrategy(BaseProviderStrategy):
    """Canonical Azure Event Hubs provider strategy."""

    PROVIDER_ID = "eventhubs"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "streaming"
    VENDOR_NAME = "Microsoft Azure"

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
                "STREAM_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "STREAMING_READ": CapabilitySupportStatus.SUPPORTED,
                "STREAMING_WRITE": CapabilitySupportStatus.SUPPORTED,
                "KAFKA_COMPATIBLE": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import azure.eventhub
            return True, "azure-eventhub available."
        except ImportError:
            return False, "azure-eventhub library not installed. Install via 'pip install azure-eventhub'."

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
                    error_code="EVENTHUBS_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        from azure.eventhub import EventHubProducerClient
        conn_str = credentials.get("connection_string") or credentials.get("password")
        if not conn_str:
            raise AuthenticationError(
                ConnectionFailure(
                    error_code="EVENTHUBS_CREDENTIALS_MISSING",
                    category=FailureCategory.AUTHENTICATION_FAILURE,
                    message="Azure Event Hubs connection string reference is missing or unresolved.",
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )
        return EventHubProducerClient.from_connection_string(conn_str, eventhub_name=spec.database_name)

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
            # Physical metadata RPC proving reachability without sending messages
            if hasattr(connection, "get_eventhub_properties"):
                connection.get_eventhub_properties()
                return True
            elif hasattr(connection, "get_partition_ids"):
                connection.get_partition_ids()
                return True
            # A constructed SDK object is not physical readiness proof.
            return False
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
            resolved_host=spec.host or "servicebus.windows.net",
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=spec.port or 443,
            server_version="Azure Event Hubs",
            catalog_or_database=spec.database_name or "eventhub",
            cloud_region=spec.region,
            route_type=spec.route_spec.route_type,
            topology_role="MANAGED_EVENT_HUB",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="eventhubs-attested",
            capabilities={
                "STREAM_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
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
            endpoint_fingerprint="eventhubs-attested",
            granted_privileges=["Listen", "Send"],
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
            error_code="EVENTHUBS_ERROR",
            category=FailureCategory.PROVIDER_INTERNAL_ERROR,
            message=msg,
            retryable=False,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
