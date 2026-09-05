"""
tests.unit.engine_connection.test_rabbitmq_provider
=======================================================
Dedicated hostile/unit tests for the RabbitMQ provider strategy (P7A Campaign B).

Covers RabbitMQ-specific behavior distinct from Kafka: negative capability truth
(OFFSET_COMMIT/CDC_LOG_CAPTURE/EXACTLY_ONCE/SCHEMA_REGISTRY not fabricated SUPPORTED),
fail-closed Streams-plugin probing, broker-cluster topology (not a partitioned log),
and AMQP-specific error normalization.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.streaming.rabbitmq import RabbitMQProviderStrategy


def test_static_manifest_does_not_fabricate_offset_or_exactly_once_support():
    strat = RabbitMQProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["OFFSET_COMMIT"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["EXACTLY_ONCE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["SCHEMA_REGISTRY"] == CapabilitySupportStatus.UNSUPPORTED
    # Genuinely supported AMQP capabilities remain truthfully declared.
    assert manifest.capabilities["STREAMING_READ"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["STREAMING_WRITE"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["PUBLISHER_CONFIRMS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = RabbitMQProviderStrategy()
    assert strat.PROVIDER_ID == "rabbitmq"
    manifest = strat.get_static_manifest()
    assert manifest.family == "streaming"


def test_validate_configuration_requires_host_or_endpoints():
    strat = RabbitMQProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="rabbitmq", host=""))

    # Valid spec does not raise.
    strat.validate_configuration(EndpointSpec(provider_id="rabbitmq", host="rabbitmq.internal"))


def test_probe_capabilities_fails_closed_on_channel_exception():
    strat = RabbitMQProviderStrategy()

    class ExplodingConnection:
        def channel(self):
            raise RuntimeError("connection reset")

    spec = EndpointSpec(provider_id="rabbitmq", host="rabbitmq.internal")
    snapshot = strat.probe_capabilities(ExplodingConnection(), spec)

    assert snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_probe_capabilities_never_claims_cdc_support_from_bare_channel():
    strat = RabbitMQProviderStrategy()

    class FakeChannel:
        def close(self):
            pass

    class FakeConnection:
        def channel(self):
            return FakeChannel()

    spec = EndpointSpec(provider_id="rabbitmq", host="rabbitmq.internal")
    snapshot = strat.probe_capabilities(FakeConnection(), spec)

    # A live AMQP channel alone proves connectivity, not that the Streams plugin is
    # enabled -- must never elevate to SUPPORTED without a management-API probe.
    assert snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_probe_permissions_never_claims_cdc_capability():
    strat = RabbitMQProviderStrategy()

    class FakeChannel:
        def close(self):
            pass

    class FakeConnection:
        def channel(self):
            return FakeChannel()

    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="rabbitmq", host="rabbitmq.internal")
    snapshot = strat.probe_permissions(FakeConnection(), spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_cdc is False


def test_attest_physical_identity_reports_broker_cluster_not_partitioned_log():
    strat = RabbitMQProviderStrategy()
    spec = EndpointSpec(provider_id="rabbitmq", host="rabbitmq.internal")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="rabbitmq.internal", effective_port=5672, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "BROKER_CLUSTER"


def test_normalize_error_auth_failure():
    strat = RabbitMQProviderStrategy()

    class AccessRefused(Exception):
        pass

    failure = strat.normalize_error(AccessRefused("ACCESS_REFUSED - login was refused"))
    assert failure.error_code == "RABBITMQ_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_broker_unavailable_is_retryable():
    strat = RabbitMQProviderStrategy()

    class AMQPConnectionError(Exception):
        pass

    failure = strat.normalize_error(AMQPConnectionError("Connection refused"))
    assert failure.error_code == "RABBITMQ_BROKER_UNAVAILABLE"
    assert failure.retryable is True


def test_normalize_error_permission_denied_not_retryable():
    strat = RabbitMQProviderStrategy()

    class OperationError(Exception):
        pass

    failure = strat.normalize_error(OperationError("NOT_AUTHORIZED - permission denied"))
    assert failure.error_code == "RABBITMQ_PERMISSION_DENIED"
    assert failure.retryable is False


def test_is_dependency_available_truthfully_reports_missing_pika():
    strat = RabbitMQProviderStrategy()
    avail, msg = strat.is_dependency_available()
    # pika is not installed in this environment -- must truthfully report unavailable,
    # never silently claim availability.
    assert avail is False
    assert "pika" in msg


def test_connect_raises_dependency_missing_when_pika_unavailable():
    strat = RabbitMQProviderStrategy()

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="rabbitmq", host="rabbitmq.internal")
    route = ResolvedRoute(effective_host="rabbitmq.internal", effective_port=5672, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})
