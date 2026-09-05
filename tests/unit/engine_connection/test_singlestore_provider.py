"""
tests.unit.engine_connection.test_singlestore_provider
==========================================================
Dedicated hostile/unit tests for the SingleStore provider strategy (P7A Campaign B).

Covers negative capability truth (FOREIGN_KEYS/CDC_LOG_CAPTURE not fabricated),
aggregator/leaf topology truth, and SingleStore-specific error normalization.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.relational.singlestore import SingleStoreProviderStrategy


def test_static_manifest_does_not_fabricate_foreign_keys_or_cdc():
    strat = SingleStoreProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["FOREIGN_KEYS"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["COLUMNAR_STORAGE"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["TRANSACTIONS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = SingleStoreProviderStrategy()
    assert strat.PROVIDER_ID == "singlestore"
    manifest = strat.get_static_manifest()
    assert manifest.family == "relational"


def test_validate_configuration_requires_host():
    strat = SingleStoreProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="singlestore", host=""))

    strat.validate_configuration(EndpointSpec(provider_id="singlestore", host="s2.internal"))


def test_probe_permissions_never_claims_cdc_capability():
    strat = SingleStoreProviderStrategy()
    from akaalEngine.connection.models.session import SessionPurpose

    spec = EndpointSpec(provider_id="singlestore", host="s2.internal")
    snapshot = strat.probe_permissions(object(), spec, SessionPurpose.BULK_SOURCE_READ)
    assert snapshot.can_cdc is False


def test_attest_physical_identity_reports_aggregator_leaf_topology():
    strat = SingleStoreProviderStrategy()
    spec = EndpointSpec(provider_id="singlestore", host="s2.internal")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="s2.internal", effective_port=3306, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "AGGREGATOR_LEAF_CLUSTER"


def test_normalize_error_deadlock_is_retryable():
    strat = SingleStoreProviderStrategy()

    class FakeError(Exception):
        args = (1213, "Deadlock found")

    failure = strat.normalize_error(FakeError())
    assert failure.error_code == "SINGLESTORE_DEADLOCK_OR_LOCK_TIMEOUT"
    assert failure.retryable is True


def test_normalize_error_auth_failure_not_retryable():
    strat = SingleStoreProviderStrategy()

    class FakeError(Exception):
        args = (1045, "Access denied")

    failure = strat.normalize_error(FakeError())
    assert failure.error_code == "SINGLESTORE_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_leaf_unavailable_is_retryable():
    strat = SingleStoreProviderStrategy()

    class FakeError(Exception):
        args = (2003, "Can't connect to SingleStore server")

    failure = strat.normalize_error(FakeError())
    assert failure.error_code == "SINGLESTORE_LEAF_UNAVAILABLE"
    assert failure.retryable is True


def test_is_dependency_available_reflects_real_pymysql_state():
    strat = SingleStoreProviderStrategy()
    avail, msg = strat.is_dependency_available()
    assert avail is True
    assert "PyMySQL" in msg


def test_connect_raises_dependency_missing_when_driver_unavailable(monkeypatch):
    strat = SingleStoreProviderStrategy()
    monkeypatch.setattr(strat, "is_dependency_available", lambda: (False, "PyMySQL library not installed."))

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="singlestore", host="s2.internal")
    route = ResolvedRoute(effective_host="s2.internal", effective_port=3306, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})


def test_validate_returns_false_for_none_connection():
    strat = SingleStoreProviderStrategy()
    assert strat.validate(None) is False
