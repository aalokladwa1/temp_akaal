"""
tests.unit.engine_connection.test_influxdb_provider
=======================================================
Dedicated hostile/unit tests for the InfluxDB provider strategy (P7A Campaign B,
the Engine's first time-series-family provider).

Covers negative capability truth (TRANSACTIONS/CDC_LOG_CAPTURE not fabricated --
InfluxDB genuinely has neither concept), time-series-engine topology truth, and
InfluxDB-specific error normalization.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.timeseries.influxdb import InfluxDBProviderStrategy


def test_static_manifest_does_not_fabricate_transactions_or_cdc():
    strat = InfluxDBProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["TRANSACTIONS"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["TIME_SERIES_NATIVE"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["RETENTION_POLICY_MANAGEMENT"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = InfluxDBProviderStrategy()
    assert strat.PROVIDER_ID == "influxdb"
    manifest = strat.get_static_manifest()
    assert manifest.family == "timeseries"


def test_validate_configuration_requires_host():
    strat = InfluxDBProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="influxdb", host=""))

    strat.validate_configuration(EndpointSpec(provider_id="influxdb", host="influxdb.internal"))


def test_probe_permissions_never_claims_cdc_capability():
    strat = InfluxDBProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="influxdb", host="influxdb.internal")
    snapshot = strat.probe_permissions(object(), spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_cdc is False


def test_probe_permissions_reports_no_privileges_without_connection():
    strat = InfluxDBProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="influxdb", host="influxdb.internal")
    snapshot = strat.probe_permissions(None, spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.granted_privileges == []


def test_attest_physical_identity_reports_time_series_engine_topology():
    strat = InfluxDBProviderStrategy()
    spec = EndpointSpec(provider_id="influxdb", host="influxdb.internal")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="influxdb.internal", effective_port=8086, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "TIME_SERIES_ENGINE"


def test_normalize_error_auth_failure():
    strat = InfluxDBProviderStrategy()
    failure = strat.normalize_error(Exception("unauthorized access: invalid token"))
    assert failure.error_code == "INFLUXDB_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_permission_denied():
    strat = InfluxDBProviderStrategy()
    failure = strat.normalize_error(Exception("forbidden: insufficient permissions to write"))
    assert failure.error_code == "INFLUXDB_PERMISSION_DENIED"
    assert failure.retryable is False


def test_normalize_error_rate_limited_is_retryable():
    strat = InfluxDBProviderStrategy()
    failure = strat.normalize_error(Exception("too many requests, 429"))
    assert failure.error_code == "INFLUXDB_RATE_LIMITED"
    assert failure.retryable is True


def test_normalize_error_unavailable_is_retryable():
    strat = InfluxDBProviderStrategy()
    failure = strat.normalize_error(Exception("connection refused"))
    assert failure.error_code == "INFLUXDB_UNAVAILABLE"
    assert failure.retryable is True


def test_is_dependency_available_truthfully_reports_missing_client():
    strat = InfluxDBProviderStrategy()
    avail, msg = strat.is_dependency_available()
    assert avail is False
    assert "influxdb-client" in msg


def test_connect_raises_dependency_missing_when_client_unavailable():
    strat = InfluxDBProviderStrategy()

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="influxdb", host="influxdb.internal")
    route = ResolvedRoute(effective_host="influxdb.internal", effective_port=8086, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})


def test_validate_returns_false_for_none_connection():
    strat = InfluxDBProviderStrategy()
    assert strat.validate(None) is False
