"""
tests.unit.engine_connection.test_clickhouse_provider
=========================================================
Dedicated hostile/unit tests for the ClickHouse provider strategy (P7A Campaign B).

Covers negative capability truth (TRANSACTIONS/CDC_LOG_CAPTURE not fabricated),
distributed-cluster topology truth, and ClickHouse-specific error normalization.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.warehouse.clickhouse import ClickHouseProviderStrategy


def test_static_manifest_does_not_fabricate_transactions_or_cdc():
    strat = ClickHouseProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["TRANSACTIONS"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["MUTATIONS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["COLUMNAR_STORAGE"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = ClickHouseProviderStrategy()
    assert strat.PROVIDER_ID == "clickhouse"
    manifest = strat.get_static_manifest()
    assert manifest.family == "warehouse"


def test_validate_configuration_requires_host():
    strat = ClickHouseProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="clickhouse", host=""))

    strat.validate_configuration(EndpointSpec(provider_id="clickhouse", host="clickhouse.internal"))


def test_probe_permissions_never_claims_cdc_capability():
    strat = ClickHouseProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="clickhouse", host="clickhouse.internal")
    snapshot = strat.probe_permissions(object(), spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_cdc is False


def test_attest_physical_identity_reports_distributed_topology():
    strat = ClickHouseProviderStrategy()
    spec = EndpointSpec(provider_id="clickhouse", host="clickhouse.internal")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="clickhouse.internal", effective_port=8123, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "DISTRIBUTED"


def test_normalize_error_auth_failure():
    strat = ClickHouseProviderStrategy()
    failure = strat.normalize_error(Exception("Authentication failed: password is incorrect"))
    assert failure.error_code == "CLICKHOUSE_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_permission_denied():
    strat = ClickHouseProviderStrategy()
    failure = strat.normalize_error(Exception("Not enough privileges to SELECT from table"))
    assert failure.error_code == "CLICKHOUSE_PERMISSION_DENIED"
    assert failure.retryable is False


def test_normalize_error_memory_limit_not_retryable():
    strat = ClickHouseProviderStrategy()
    failure = strat.normalize_error(Exception("Memory limit (for query) exceeded"))
    assert failure.error_code == "CLICKHOUSE_MEMORY_LIMIT_EXCEEDED"
    assert failure.retryable is False


def test_normalize_error_too_many_queries_is_retryable():
    strat = ClickHouseProviderStrategy()
    failure = strat.normalize_error(Exception("Too many simultaneous queries"))
    assert failure.error_code == "CLICKHOUSE_TOO_MANY_QUERIES"
    assert failure.retryable is True


def test_normalize_error_unavailable_is_retryable():
    strat = ClickHouseProviderStrategy()
    failure = strat.normalize_error(Exception("Connection refused"))
    assert failure.error_code == "CLICKHOUSE_UNAVAILABLE"
    assert failure.retryable is True


def test_is_dependency_available_truthfully_reports_missing_client():
    strat = ClickHouseProviderStrategy()
    avail, msg = strat.is_dependency_available()
    assert avail is False
    assert "clickhouse-connect" in msg


def test_connect_raises_dependency_missing_when_client_unavailable():
    strat = ClickHouseProviderStrategy()

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="clickhouse", host="clickhouse.internal")
    route = ResolvedRoute(effective_host="clickhouse.internal", effective_port=8123, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})


def test_validate_returns_false_for_none_connection():
    strat = ClickHouseProviderStrategy()
    assert strat.validate(None) is False
