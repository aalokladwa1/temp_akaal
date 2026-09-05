"""
tests.unit.engine_connection.test_yugabytedb_provider
=========================================================
Dedicated hostile/unit tests for the YugabyteDB provider strategy (P7A Campaign B).

Covers negative capability truth (CDC_LOG_CAPTURE not fabricated), fail-closed
replication-slot probing, distributed topology truth, and SQLSTATE 40001 distributed
transaction-conflict semantics.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.providers.relational.yugabytedb import YugabyteDBProviderStrategy


def test_static_manifest_does_not_fabricate_cdc_support():
    strat = YugabyteDBProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["TRANSACTIONS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["DISTRIBUTED_TOPOLOGY"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = YugabyteDBProviderStrategy()
    assert strat.PROVIDER_ID == "yugabytedb"
    manifest = strat.get_static_manifest()
    assert manifest.family == "relational"


def test_validate_configuration_requires_host_and_database():
    strat = YugabyteDBProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="yugabytedb", host="", database_name="yugabyte"))

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="yugabytedb", host="yb.internal", database_name=""))

    strat.validate_configuration(EndpointSpec(provider_id="yugabytedb", host="yb.internal", database_name="yugabyte"))


def test_probe_capabilities_fails_closed_on_probe_exception():
    strat = YugabyteDBProviderStrategy()

    class ExplodingCursor:
        def execute(self, *a, **kw):
            raise RuntimeError("insufficient privilege")

        def close(self):
            pass

    class ExplodingConnection:
        def cursor(self):
            return ExplodingCursor()

    spec = EndpointSpec(provider_id="yugabytedb", host="yb.internal", database_name="yugabyte")
    snapshot = strat.probe_capabilities(ExplodingConnection(), spec)
    assert snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_probe_capabilities_reports_supported_only_on_truthful_replication_slot():
    strat = YugabyteDBProviderStrategy()

    class SlotCursor:
        def __init__(self, has_slot: bool):
            self._has_slot = has_slot

        def execute(self, sql, *a, **kw):
            pass

        def fetchall(self):
            return [("yboutput",)] if self._has_slot else []

        def close(self):
            pass

    class SlotConnection:
        def __init__(self, has_slot: bool):
            self._has_slot = has_slot

        def cursor(self):
            return SlotCursor(self._has_slot)

    spec = EndpointSpec(provider_id="yugabytedb", host="yb.internal", database_name="yugabyte")

    with_slot = strat.probe_capabilities(SlotConnection(True), spec)
    assert with_slot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.SUPPORTED

    without_slot = strat.probe_capabilities(SlotConnection(False), spec)
    assert without_slot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_attest_physical_identity_reports_distributed_not_primary():
    strat = YugabyteDBProviderStrategy()
    spec = EndpointSpec(provider_id="yugabytedb", host="yb.internal", database_name="yugabyte")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="yb.internal", effective_port=5433, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    assert identity.topology_role == "DISTRIBUTED"


def test_normalize_error_sqlstate_40001_is_retryable_transaction_conflict():
    strat = YugabyteDBProviderStrategy()

    class FakeError(Exception):
        pgcode = "40001"

    failure = strat.normalize_error(FakeError("could not serialize access due to concurrent update"))
    assert failure.error_code == "YUGABYTEDB_TRANSACTION_CONFLICT"
    assert failure.retryable is True


def test_normalize_error_auth_failure_not_retryable():
    strat = YugabyteDBProviderStrategy()

    class FakeError(Exception):
        pgcode = "28P01"

    failure = strat.normalize_error(FakeError("password authentication failed"))
    assert failure.error_code == "YUGABYTEDB_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_tserver_unavailable_is_retryable():
    strat = YugabyteDBProviderStrategy()

    class FakeError(Exception):
        pgcode = "57P01"

    failure = strat.normalize_error(FakeError("terminating connection due to administrator command"))
    assert failure.error_code == "YUGABYTEDB_TSERVER_UNAVAILABLE"
    assert failure.retryable is True


def test_is_dependency_available_reflects_real_psycopg2_state():
    strat = YugabyteDBProviderStrategy()
    avail, msg = strat.is_dependency_available()
    assert avail is True
    assert "psycopg2" in msg


def test_connect_raises_dependency_missing_when_driver_unavailable(monkeypatch):
    strat = YugabyteDBProviderStrategy()
    monkeypatch.setattr(strat, "is_dependency_available", lambda: (False, "psycopg2 library not installed."))

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="yugabytedb", host="yb.internal", database_name="yugabyte")
    route = ResolvedRoute(effective_host="yb.internal", effective_port=5433, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})
