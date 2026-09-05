"""
tests.unit.engine_connection.test_tidb_provider
===================================================
Dedicated hostile/unit tests for the TiDB provider strategy (P7A Campaign B).

Covers negative capability truth (SAVEPOINTS/CDC_LOG_CAPTURE not fabricated -- unlike
MySQL, TiDB does not use binlog for CDC and has version-gated SAVEPOINT support),
distributed topology truth, and TiDB-specific error normalization.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.relational.tidb import TiDBProviderStrategy


def test_static_manifest_does_not_fabricate_savepoints_or_cdc():
    strat = TiDBProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["SAVEPOINTS"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["TRANSACTIONS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["DISTRIBUTED_TOPOLOGY"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = TiDBProviderStrategy()
    assert strat.PROVIDER_ID == "tidb"
    manifest = strat.get_static_manifest()
    assert manifest.family == "relational"


def test_validate_configuration_requires_host():
    strat = TiDBProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="tidb", host=""))

    strat.validate_configuration(EndpointSpec(provider_id="tidb", host="tidb.internal"))


def test_probe_permissions_never_claims_cdc_capability():
    strat = TiDBProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="tidb", host="tidb.internal")
    snapshot = strat.probe_permissions(object(), spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_cdc is False


def test_attest_physical_identity_reports_distributed_not_primary():
    strat = TiDBProviderStrategy()
    spec = EndpointSpec(provider_id="tidb", host="tidb.internal")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="tidb.internal", effective_port=4000, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "DISTRIBUTED"


def test_normalize_error_write_conflict_is_retryable():
    strat = TiDBProviderStrategy()

    class FakeError(Exception):
        args = (9007, "Write conflict")

    failure = strat.normalize_error(FakeError())
    assert failure.error_code == "TIDB_WRITE_CONFLICT"
    assert failure.retryable is True


def test_normalize_error_auth_failure_not_retryable():
    strat = TiDBProviderStrategy()

    class FakeError(Exception):
        args = (1045, "Access denied")

    failure = strat.normalize_error(FakeError())
    assert failure.error_code == "TIDB_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_server_unavailable_is_retryable():
    strat = TiDBProviderStrategy()

    class FakeError(Exception):
        args = (2003, "Can't connect to TiDB server")

    failure = strat.normalize_error(FakeError())
    assert failure.error_code == "TIDB_SERVER_UNAVAILABLE"
    assert failure.retryable is True


def test_is_dependency_available_reflects_real_pymysql_state():
    strat = TiDBProviderStrategy()
    avail, msg = strat.is_dependency_available()
    assert avail is True
    assert "PyMySQL" in msg


def test_connect_raises_dependency_missing_when_driver_unavailable(monkeypatch):
    strat = TiDBProviderStrategy()
    monkeypatch.setattr(strat, "is_dependency_available", lambda: (False, "PyMySQL library not installed."))

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="tidb", host="tidb.internal")
    route = ResolvedRoute(effective_host="tidb.internal", effective_port=4000, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})


def test_validate_returns_false_for_none_connection():
    strat = TiDBProviderStrategy()
    assert strat.validate(None) is False
