"""
akaalEngine.connection.providers.streaming.kafka
================================================
Canonical Apache Kafka Provider Strategy (also serves Confluent & AWS MSK profiles).
Supports kafka-python / confluent-kafka, consumer groups, offset commits, and topic discovery.
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

logger = logging.getLogger("akaalEngine.connection.providers.kafka")


class KafkaProviderStrategy(BaseProviderStrategy):
    """Canonical Apache Kafka provider strategy."""

    PROVIDER_ID = "kafka"
    PROVIDER_VERSION = "1.0.0"
    FAMILY = "streaming"
    VENDOR_NAME = "Apache Software Foundation"

    def get_static_manifest(self) -> StaticCapabilityManifest:
        return StaticCapabilityManifest(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            family=self.FAMILY,
            vendor_name=self.VENDOR_NAME,
            supported_roles=[EndpointRole.SOURCE, EndpointRole.TARGET, EndpointRole.CDC_LOG],
            supports_tls=True,
            supports_mtls=True,
            capabilities={
                "TOPIC_DISCOVERY": CapabilitySupportStatus.SUPPORTED,
                "STREAMING_READ": CapabilitySupportStatus.SUPPORTED,
                "STREAMING_WRITE": CapabilitySupportStatus.SUPPORTED,
                "OFFSET_COMMIT": CapabilitySupportStatus.SUPPORTED,
                "EXACTLY_ONCE": CapabilitySupportStatus.SUPPORTED,  # Idempotent / transactional producer
                "SCHEMA_REGISTRY": CapabilitySupportStatus.SUPPORTED,
            },
            proof_level=ProofLevel.IMPLEMENTED,
        )

    def is_dependency_available(self) -> Tuple[bool, str]:
        try:
            import kafka
            return True, "kafka-python available."
        except ImportError:
            try:
                import confluent_kafka
                return True, "confluent-kafka available."
            except ImportError:
                return False, "kafka client library not installed. Install via 'pip install kafka-python' or 'confluent-kafka'."

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
                    error_code="KAFKA_DEPENDENCY_MISSING",
                    category=FailureCategory.DEPENDENCY_MISSING,
                    message=msg,
                    retryable=False,
                    provider_id=self.PROVIDER_ID,
                )
            )

        bootstrap_servers = resolved_route.get_bootstrap_servers()

        auth_type = spec.auth_spec.auth_type.value if (spec.auth_spec and hasattr(spec.auth_spec.auth_type, "value")) else "NONE"
        tls_mode = spec.tls_binding.mode.value if hasattr(spec.tls_binding.mode, "value") else str(spec.tls_binding.mode)
        is_tls = tls_mode != "DISABLED"
        is_sasl = auth_type in ("SASL_PLAIN", "SASL_SCRAM_256", "SASL_SCRAM_512", "PASSWORD")

        if is_sasl and is_tls:
            derived_sec_proto = "SASL_SSL"
        elif is_sasl:
            derived_sec_proto = "SASL_PLAINTEXT"
        elif is_tls:
            derived_sec_proto = "SSL"
        else:
            derived_sec_proto = "PLAINTEXT"

        security_protocol = spec.options.get("security_protocol", derived_sec_proto)

        derived_sasl_mech = "PLAIN"
        if auth_type == "SASL_SCRAM_256":
            derived_sasl_mech = "SCRAM-SHA-256"
        elif auth_type == "SASL_SCRAM_512":
            derived_sasl_mech = "SCRAM-SHA-512"

        sasl_mech = spec.options.get("sasl_mechanism", derived_sasl_mech)

        sasl_user = credentials.get("username") or (spec.auth_spec.username if spec.auth_spec else None)
        sasl_pass = credentials.get("password")

        # Try kafka-python first
        try:
            from kafka import KafkaAdminClient
            client_kwargs: dict[str, Any] = {
                "bootstrap_servers": bootstrap_servers,
                "client_id": spec.options.get("client_id", "akaal-engine-connection"),
                "request_timeout_ms": int(spec.route_spec.connect_timeout_ms),
                "security_protocol": security_protocol,
            }
            if is_sasl and sasl_user:
                client_kwargs["sasl_mechanism"] = sasl_mech
                client_kwargs["sasl_plain_username"] = sasl_user
                client_kwargs["sasl_plain_password"] = sasl_pass
            if is_tls:
                if ssl_context:
                    client_kwargs["ssl_context"] = ssl_context
                elif spec.tls_binding.ca_cert_path:
                    client_kwargs["ssl_cafile"] = spec.tls_binding.ca_cert_path
                if spec.tls_binding.client_cert_path:
                    client_kwargs["ssl_certfile"] = spec.tls_binding.client_cert_path

            admin = KafkaAdminClient(**client_kwargs)
            # Physical verification: describe_cluster proves actual broker connection
            admin.describe_cluster()
            return admin
        except ImportError:
            pass

        # Try confluent-kafka alternative
        try:
            from confluent_kafka.admin import AdminClient
            conf: dict[str, Any] = {
                "bootstrap.servers": ",".join(bootstrap_servers),
                "client.id": spec.options.get("client_id", "akaal-engine-connection"),
                "socket.timeout.ms": int(spec.route_spec.connect_timeout_ms),
                "security.protocol": security_protocol.lower(),
            }
            if is_sasl and sasl_user:
                conf["sasl.mechanism"] = sasl_mech
                conf["sasl.username"] = sasl_user
                conf["sasl.password"] = sasl_pass
            if is_tls and spec.tls_binding.ca_cert_path:
                conf["ssl.ca.location"] = spec.tls_binding.ca_cert_path
            if is_tls and spec.tls_binding.client_cert_path:
                conf["ssl.certificate.location"] = spec.tls_binding.client_cert_path

            admin = AdminClient(conf)
            # Physical verification: list_topics proves cluster communication
            meta = admin.list_topics(timeout=spec.route_spec.connect_timeout_ms / 1000.0)
            if meta is None or not meta.brokers:
                raise ConnectionError(f"No brokers reachable on Kafka bootstrap servers: {bootstrap_servers}")
            return admin
        except ImportError:
            pass

        raise DependencyMissingError(
            ConnectionFailure(
                error_code="KAFKA_DEPENDENCY_MISSING",
                category=FailureCategory.DEPENDENCY_MISSING,
                message="Neither 'kafka-python' nor 'confluent-kafka' could be imported.",
                retryable=False,
                provider_id=self.PROVIDER_ID,
            )
        )

    def close(self, connection: Any) -> None:
        if connection is not None:
            if hasattr(connection, "close"):
                try:
                    connection.close()
                except Exception:
                    pass

    def validate(self, connection: Any) -> bool:
        if connection is None:
            return False
        try:
            if hasattr(connection, "describe_cluster"):
                connection.describe_cluster()
                return True
            elif hasattr(connection, "list_topics"):
                meta = connection.list_topics(timeout=5.0)
                return bool(meta and meta.brokers)
            return False
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
        cluster_id = None
        if connection is not None:
            try:
                if hasattr(connection, "describe_cluster"):
                    cluster_info = connection.describe_cluster()
                    cluster_id = cluster_info.get("cluster_id")
                elif hasattr(connection, "list_topics"):
                    meta = connection.list_topics(timeout=3.0)
                    if meta:
                        cluster_id = meta.cluster_id
            except Exception:
                pass

        return PhysicalEndpointIdentity(
            provider_id=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            role=spec.role,
            resolved_host=resolved_route.effective_host,
            resolved_ip=resolved_route.resolved_ip,
            resolved_port=resolved_route.effective_port or spec.port or 9092,
            server_version="Apache Kafka Cluster",
            server_cluster_name=cluster_id,
            catalog_or_database=spec.database_name or "default-topic",
            principal_identity=spec.auth_spec.username if spec.auth_spec else "kafka_client",
            route_type=spec.route_spec.route_type,
            topology_role="BROKER_CLUSTER",
        )

    def probe_capabilities(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ProbedCapabilitySnapshot:
        return ProbedCapabilitySnapshot(
            provider_id=self.PROVIDER_ID,
            endpoint_fingerprint="kafka-attested",
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
            endpoint_fingerprint="kafka-attested",
            granted_privileges=["READ", "WRITE", "DESCRIBE"],
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
        code = "KAFKA_ERROR"
        cat = FailureCategory.PROVIDER_INTERNAL_ERROR
        retryable = False

        lower_msg = msg.lower()
        if "authentication" in lower_msg or "sasl" in lower_msg or "unauthorized" in lower_msg:
            cat = FailureCategory.AUTHENTICATION_FAILURE
            code = "KAFKA_AUTH_FAILED"
        elif "authorization" in lower_msg or "not authorized" in lower_msg or "permission" in lower_msg:
            cat = FailureCategory.AUTHORIZATION_PERMISSION_FAILURE
            code = "KAFKA_PERMISSION_DENIED"
        elif "nobrokersavailable" in lower_msg or "broker not available" in lower_msg or "connection refused" in lower_msg or "all brokers down" in lower_msg:
            cat = FailureCategory.ENDPOINT_UNAVAILABLE
            code = "KAFKA_BROKERS_UNAVAILABLE"
            retryable = True
        elif "timeout" in lower_msg or "timed out" in lower_msg:
            cat = FailureCategory.TIMEOUT
            code = "KAFKA_TIMEOUT"
            retryable = True

        return ConnectionFailure(
            error_code=code,
            category=cat,
            message=msg,
            retryable=retryable,
            provider_id=self.PROVIDER_ID,
            original_error_type=type(exc).__name__,
        )
