"""
tests.unit.engine_connection.test_cockroachdb_provider
========================================================
Dedicated hostile/unit tests for the CockroachDB provider strategy (P7A Campaign B).

Covers CockroachDB-specific behavior that differs from the PostgreSQL strategy it reuses
psycopg2 from: negative capability truth (CDC_LOG_CAPTURE/BINARY_COPY not fabricated
SUPPORTED), fail-closed capability probing, SQLSTATE 40001 retry semantics, truthful
distributed topology reporting, and configuration validation.
"""

from __future__ import annotations

import pytest

from akaalEngine.connection.models.capability import CapabilitySupportStatus, ProofLevel
from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
from akaalEngine.connection.providers.relational.cockroachdb import CockroachDBProviderStrategy


def test_static_manifest_does_not_fabricate_cdc_or_binary_copy_support():
    strat = CockroachDBProviderStrategy()
    manifest = strat.get_static_manifest()

    assert manifest.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED
    assert manifest.capabilities["BINARY_COPY"] == CapabilitySupportStatus.UNSUPPORTED
    # Genuinely supported distributed-SQL capabilities remain truthfully declared.
    assert manifest.capabilities["TRANSACTIONS"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["SERIALIZABLE_RETRY_REQUIRED"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.capabilities["DISTRIBUTED_TOPOLOGY"] == CapabilitySupportStatus.SUPPORTED
    assert manifest.proof_level == ProofLevel.IMPLEMENTED


def test_provider_id_and_family():
    strat = CockroachDBProviderStrategy()
    assert strat.PROVIDER_ID == "cockroachdb"
    manifest = strat.get_static_manifest()
    assert manifest.family == "relational"
    assert manifest.vendor_name == "Cockroach Labs"


def test_validate_configuration_requires_host_and_database():
    strat = CockroachDBProviderStrategy()

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="cockroachdb", host="", database_name="defaultdb"))

    with pytest.raises(ValueError):
        strat.validate_configuration(EndpointSpec(provider_id="cockroachdb", host="crdb.internal", database_name=""))

    # Valid spec does not raise.
    strat.validate_configuration(EndpointSpec(provider_id="cockroachdb", host="crdb.internal", database_name="defaultdb"))


def test_probe_capabilities_fails_closed_on_probe_exception():
    strat = CockroachDBProviderStrategy()

    class ExplodingCursor:
        def execute(self, *a, **kw):
            raise RuntimeError("insufficient privilege")

        def close(self):
            pass

    class ExplodingConnection:
        def cursor(self):
            return ExplodingCursor()

    spec = EndpointSpec(provider_id="cockroachdb", host="crdb.internal", database_name="defaultdb")
    snapshot = strat.probe_capabilities(ExplodingConnection(), spec)

    # Must fail closed to UNSUPPORTED, never silently claim SUPPORTED on a failed probe.
    assert snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_probe_capabilities_reports_supported_only_on_truthful_license_probe():
    strat = CockroachDBProviderStrategy()

    class LicenseCursor:
        def __init__(self, licensed: bool):
            self._licensed = licensed
            self._last = None

        def execute(self, sql, *a, **kw):
            self._last = sql

        def fetchone(self):
            if "enterprise.license" in self._last:
                return ("some-license-value",) if self._licensed else (None,)
            return None

        def close(self):
            pass

    class LicenseConnection:
        def __init__(self, licensed: bool):
            self._licensed = licensed

        def cursor(self):
            return LicenseCursor(self._licensed)

    spec = EndpointSpec(provider_id="cockroachdb", host="crdb.internal", database_name="defaultdb")

    licensed_snapshot = strat.probe_capabilities(LicenseConnection(True), spec)
    assert licensed_snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.SUPPORTED

    unlicensed_snapshot = strat.probe_capabilities(LicenseConnection(False), spec)
    assert unlicensed_snapshot.capabilities["CDC_LOG_CAPTURE"] == CapabilitySupportStatus.UNSUPPORTED


def test_attest_physical_identity_reports_distributed_not_primary():
    strat = CockroachDBProviderStrategy()
    spec = EndpointSpec(provider_id="cockroachdb", host="crdb.internal", database_name="defaultdb")

    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    route = ResolvedRoute(effective_host="crdb.internal", effective_port=26257, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    identity = strat.attest_physical_identity(None, spec, route)
    # Never fabricate PostgreSQL's PRIMARY/REPLICA convention for a leaderless cluster.
    assert identity.topology_role == "DISTRIBUTED"


def test_normalize_error_sqlstate_40001_is_retryable_transaction_restart():
    strat = CockroachDBProviderStrategy()

    class FakeError(Exception):
        pgcode = "40001"

    failure = strat.normalize_error(FakeError("restart transaction: TransactionRetryError"))
    assert failure.error_code == "COCKROACHDB_TRANSACTION_RETRY_REQUIRED"
    assert failure.retryable is True


def test_normalize_error_auth_failure_not_retryable():
    strat = CockroachDBProviderStrategy()

    class FakeError(Exception):
        pgcode = "28P01"

    failure = strat.normalize_error(FakeError("password authentication failed"))
    assert failure.error_code == "COCKROACHDB_AUTH_FAILED"
    assert failure.retryable is False


def test_normalize_error_node_unavailable_is_retryable():
    strat = CockroachDBProviderStrategy()

    class FakeError(Exception):
        pgcode = "57P01"

    failure = strat.normalize_error(FakeError("node is shutting down"))
    assert failure.error_code == "COCKROACHDB_NODE_UNAVAILABLE"
    assert failure.retryable is True


def test_is_dependency_available_reflects_real_psycopg2_state():
    strat = CockroachDBProviderStrategy()
    avail, msg = strat.is_dependency_available()
    # psycopg2 is installed in this environment (shared with the PostgreSQL provider).
    assert avail is True
    assert "psycopg2" in msg


def test_connect_raises_dependency_missing_when_driver_unavailable(monkeypatch):
    strat = CockroachDBProviderStrategy()
    monkeypatch.setattr(strat, "is_dependency_available", lambda: (False, "psycopg2 library not installed."))

    from akaalEngine.connection.models.errors import DependencyMissingError
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="cockroachdb", host="crdb.internal", database_name="defaultdb")
    route = ResolvedRoute(effective_host="crdb.internal", effective_port=26257, resolved_ip="10.0.0.1", dns_time_ms=1.0, route_type=RouteType.DIRECT)

    with pytest.raises(DependencyMissingError):
        strat.connect(spec, route, {})
