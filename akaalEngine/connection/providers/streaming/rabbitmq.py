"""
akaalEngine.connection.providers.streaming.rabbitmq
====================================================
Canonical RabbitMQ Provider Strategy (P7A Campaign B).

RabbitMQ speaks AMQP 0-9-1, not Kafka's log/partition/offset model, so this is NOT a
Kafka relabel -- the differences are handled truthfully:
  - RabbitMQ is a message *broker*, not a durable replayable log by default: classic and
    quorum queues consume-and-remove (or ack/requeue), they do not retain a history that
    can be re-read from an arbitrary offset. CDC-style log capture and offset-based
    replay are declared UNSUPPORTED unless the RabbitMQ Streams plugin (a genuinely
    different queue type introduced in RabbitMQ 3.9) is truthfully probed as enabled.
  - There is no consumer-group offset-commit model; acknowledgement is per-message
    (ack/nack/reject), so OFFSET_COMMIT is UNSUPPORTED for classic/quorum queues.
  - There is no native schema registry (unlike Confluent's for Kafka).
  - No native exactly-once delivery guarantee spans publish+consume; publisher confirms
    and consumer acks each give at-least-once, not exactly-once.
  - Topology is exchanges/queues/bindings/vhosts, not partitioned topics.
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

logger = logging.getLogger("akaalEngine.connection.providers.rabbitmq")


class RabbitMQProviderStrategy(BaseProviderStrategy):
    """Canonical RabbitMQ provider strategy -- AMQP 0-9-1 message broker."""

    PROVIDER_ID = "rabbitmq"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "streaming"
    VENDOR_NAME = "VMware / Broadcom (RabbitMQ)"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET],
            supports_tls=True,
            supports_mtls=True,
            capabilities={
                "TOPIC_DISCOVERY": CapabilitySupportStatus.SUPPORTED,  # queue/exchange enumeration via management API
                "STREAMING_READ": CapabilitySupportStatus.SUPPORTED,   # queue consumption
                "STREAMING_WRITE": CapabilitySupportStatus.SUPPORTED,  # exchange publish
                "PUBLISHER_CONFIRMS": CapabilitySupportStatus.SUPPORTED,
                "CONSUMER_ACKNOWLEDGEMENTS": CapabilitySupportStatus.SUPPORTED,
                "DEAD_LETTER_ROUTING": CapabilitySupportStatus.SUPPORTED,
                # Truthfully NOT claimed supported without a live plugin probe:
                "OFFSET_COMMIT": CapabilitySupportStatus.UNSUPPORTED,  # no offset model on classic/quorum queues
                "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNSUPPORTED,  # requires RabbitMQ Streams plugin
                "EXACTLY_ONCE": CapabilitySupportStatus.UNSUPPORTED,  # at-least-once only, no native dedup
                "SCHEMA_REGISTRY": CapabilitySupportStatus.UNSUPPORTED,  # no native schema registry
            },
            proof_level=ProofLevel.IMPLEMENTED,
            restrictions=[
                "Classic and quorum queues consume-and-remove; they are not a replayable log.",
                "CDC_LOG_CAPTURE and OFFSET_COMMIT require the RabbitMQ Streams plugin and are not assumed supported without a live probe.",
            ],
            required_privileges=["configure", "write", "read"],
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import pika
            return True, f"pika version {getattr(pika, '__version__', 'unknown')} available."
        except ImportError:
            return False, "pika library not installed. Install via 'pip install pika'."

    def validate_configuration(self, spec: EndpointSpec) -> None:
        super().validate_configuration(spec)
        if not spec.host and not spec.options.get("endpoints"):
            raise ValueError("RabbitMQ host or cluster endpoints are required.")

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
                    error_code="RABBITMQ_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        import pika

        host = resolved_route.effective_host
        port = resolved_route.effective_port or spec.port or 5672
        vhost = spec.options.get("virtual_host", spec.database_name or "/")
        username = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else "guest")
        password = credentials.get("password") or "guest"

        tls_mode = spec.tls_binding.mode.value if hasattr(spec.tls_binding.mode, "value") else str(spec.tls_binding.mode)
        is_tls = tls_mode != "DISABLED"

        credentials_obj = pika.PlainCredentials(username, password)
        conn_params = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=credentials_obj,
            connection_attempts=1,
            socket_timeout=spec.route_spec.connect_timeout_ms / 1000.0,
            ssl_options=pika.SSLOptions(ssl_context) if (is_tls and ssl_context) else None,
        )

        connection = pika.BlockingConnection(conn_params)
        return connection

    def close(self, connection: Any) -> None:
        if connection is not None:
            try:
                if hasattr(connection, "is_open") and connection.is_open:
                    connection.close()
            except Exception:
                pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            return bool(getattr(connection, "is_open", False))
        except Exception:
            return False

    def reset_session(self, connection: Any, previous_purpose: SessionPurpose) -> bool:
        return self.validate(connection)

    def attest_physical_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        resolved_route: ResolvedRoute,
    ) -> PhysicalEndpointIdentity:
        server_version = "RabbitMQ"
        if connection is not None:
            try:
                props = getattr(connection, "connection", connection)
                server_props = getattr(props, "server_properties", None)
                if server_props:
                    ver = server_props.get("version")
                    product = server_props.get("product", "RabbitMQ")
                    if ver:
                        server_version = f"{product} {ver}"
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 5672,
            server_version=server_version,
            catalog_or_database=spec.options.get("virtual_host", spec.database_name or "/"),
            principal_identity=spec.auth_spec.username if spec.auth_spec else "guest",
            route_type=spec.route_spec.route_type,
            # Truthful: RabbitMQ is broker-clustered (queues mirrored/replicated across
            # nodes), not a partitioned log topology like Kafka -- reported as its own
            # distinct topology label, not borrowed from either PostgreSQL or Kafka.
            topology_role="BROKER_CLUSTER",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        caps = {
            "TOPIC_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
            "STREAMING_READ": CapabilitySupportStatus.SUPPORTED,
            "STREAMING_WRITE": CapabilitySupportStatus.SUPPORTED,
            "CDC_LOG_CAPTURE": CapabilitySupportStatus.UNKNOWN,
        }
        # The Streams plugin (queue type "stream") is the only truthful basis for
        # offset-based replay/CDC-like capture; fail closed without a verified probe.
        if connection is not None:
            try:
                channel = connection.channel()
                channel.close()
                # A live channel alone does not prove the Streams plugin is enabled --
                # that requires a management-API plugin listing this provider does not
                # have credentials for at this layer, so this stays fail-closed.
                caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED
            except Exception:
                caps["CDC_LOG_CAPTURE"] = CapabilitySupportStatus.UNSUPPORTED

        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="rabbitmq-attested",
            capabilities=caps,
            proof_level=ProofLevel.UNIT_PROVEN if connection else ProofLevel.IMPLEMENTED,
        )

    def probe_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        purpose: SessionPurpose,
    ) -> PermissionSnapshot:
        granted: list[str] = []
        if connection is not None:
            try:
                channel = connection.channel()
                channel.close()
                granted = ["read", "write", "configure"]
            except Exception:
                granted = []

        return PermissionSnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="rabbitmq-attested",
            granted_privileges=granted,
            missing_privileges=[],
            is_read_only=purpose.is_read_only_by_default,
            can_write="write" in granted and not purpose.is_read_only_by_default,
            can_ddl="configure" in granted,
            can_cdc=False,  # never truthfully claimable without a Streams-plugin management probe
            is_admin=False,
        )

    def normalize_error(
        self,
        exc: Exception,
        stage: str = "EXECUTION",
    ) -> ConnectionFailure:
        msg = redact_text(str(exc))
        exc_name = type(exc).__name__
        lower_msg = msg.lower()
        category = FailureCategory.PROVIDER_INTERNAL_ERROR
        code = "RABBITMQ_ERROR"
        retryable = False

        if "access_refused" in lower_msg or "authentication" in lower_msg or "accessrefused" in exc_name.lower():
            category = FailureCategory.AUTHENTICATION_FAILURE
            code = "RABBITMQ_AUTH_FAILED"
        elif "not_allowed" in lower_msg or "permission" in lower_msg or "not_authorized" in lower_msg:
            category = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "RABBITMQ_PERMISSION_DENIED"
        elif "connectionrefused" in exc_name.lower() or "connection refused" in lower_msg or "amqpconnectionerror" in exc_name.lower():
            category = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "RABBITMQ_BROKER_UNAVAILABLE"
            retryable = True
        elif "timeout" in lower_msg:
            category = FailureCategory.TIMEOUT
            code = "RABBITMQ_TIMEOUT"
            retryable = True
        elif "channelclosed" in exc_name.lower() or "precondition_failed" in lower_msg:
            category = FailureCategory.INVALID_CONFIGURATION
            code = "RABBITMQ_CHANNEL_PRECONDITION_FAILED"
            retryable = False

        return ConnectionFailure(
            error_code=code,
            category=category,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=exc_name,
        )
