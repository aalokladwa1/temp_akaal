"""
tests.unit.engine_connection.test_pulsar_provider
=====================================================
Dedicated hostile/unit tests for the Apache Pulsar provider strategy (P7A Campaign B).

Covers Pulsar-specific behavior distinct from Kafka: EXACTLY_ONCE/SCHEMA_REGISTRY
correctly declared UNSUPPORTED at this connector layer (real Pulsar platform features
this strategy does not wire), broker-cluster topology truth, and Pulsar-specific error
normalization.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.streaming.pulsar import PulsarProviderStrategy


def test_static_manifest_does_not_fabricate_unwired_platform_features():
    strat = PulsarProviderStrategy()
    manifest = strat.get_static_manifest()

    # Real Pulsar platform features this connector strategy does not implement wiring for.
    assert manifest.capabilities["EXACTLY_ONCE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["SCHEMA_REGISTRY"] == CapabilitySupportStatus.UNSUPPORTED
    # Genuinely implemented capabilities remain truthfully declared.
    assert manifest.capabilities["TOPIC_DISCOVERY"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["OFFSET_COMMIT"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["MULTI_TENANCY"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = PulsarProviderStrategy()
    assert strat.PROVIDER_ID == "pulsar"
    manifest = strat.get_static_manifest()
    assert manifest.family == "streaming"


def test_validate_configuration_requires_host_or_endpoints():
    strat = PulsarProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="pulsar", host=""))

    strat.validate_configuration(EndpointSpec(provider_id="pulsar", host="pulsar.internal"))


def test_probe_permissions_never_claims_cdc_capability():
    strat = PulsarProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="pulsar", host="pulsar.internal")
    snapshot = strat.probe_permissions(object(), spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_cdc is False


def test_probe_permissions_reports_no_privileges_without_connection():
    strat = PulsarProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="pulsar", host="pulsar.internal")
    snapshot = strat.probe_permissions(None, spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.granted_privileges == []
    assert snapshot.can_write is False


def test_attest_physical_identity_reports_broker_cluster_topology():
    strat = PulsarProviderStrategy()
    spec = EndpointSpec(provider_id="pulsar", host="pulsar.internal")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="pulsar.internal", effective_port=6650, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "BROKER_CLUSTER"
    assert identity.catalog_or_database == "public/default"


def test_normalize_error_auth_failure():
    strat = PulsarProviderStrategy()

    class AuthError(Exception):
        pass

    failure = strat.normalize_error(AuthError("Authentication required"))
    assert failure.error_code == "PULSAR_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_broker_unavailable_is_retryable():
    strat = PulsarProviderStrategy()

    class ConnectError(Exception):
        pass

    failure = strat.normalize_error(ConnectError("Connection refused by broker"))
    assert failure.error_code == "PULSAR_BROKER_UNAVAILABLE"
    assert failure.retryable is True


def test_normalize_error_topic_not_found_not_retryable():
    strat = PulsarProviderStrategy()

    class TopicNotFoundError(Exception):
        pass

    failure = strat.normalize_error(TopicNotFoundError("Topic not found"))
    assert failure.error_code == "PULSAR_TOPIC_NOT_FOUND"
    assert failure.retryable is False


def test_is_dependency_available_truthfully_reports_missing_pulsar_client():
    strat = PulsarProviderStrategy()
    avail, msg = strat.is_dependency_available()
    assert avail is False
    assert "pulsar-client" in msg


def test_connect_raises_dependency_missing_when_client_unavailable():
    strat = PulsarProviderStrategy()

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="pulsar", host="pulsar.internal")
    route = ResolvedRoute(effective_host="pulsar.internal", effective_port=6650, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})


def test_validate_returns_false_for_none_connection():
    strat = PulsarProviderStrategy()
    assert strat.validate(None) is False
