"""
Unit tests for akaalEngine.connection.providers conformance
===========================================================
Executes the ProviderConformanceSuite against all 28 registered provider strategies.
"""

import pytest

from akaalEngine.connection.catalog.provider_catalog import ProviderCatalog
from akaalEngine.connection.providers.conformance import ProviderConformanceSuite


def test_all_providers_pass_conformance_suite():
    catalog = ProviderCatalog.get_instance()
    providers = catalog.list_providers()

    assert len(providers) >= 28

    failed_reports = []
    for pid in providers:
        strategy = catalog.get_strategy(pid)
        report = ProviderConformanceSuite.run_suite(strategy)
        if not report.is_conformant:
            failed_reports.append(report.summary_dict())

    assert len(failed_reports) == 0, f"Provider conformance failures: {failed_reports}"


def test_sqlite_live_physical_execution():
    catalog = ProviderCatalog.get_instance()
    strategy = catalog.get_strategy("sqlite")

    is_avail, msg = strategy.is_dependency_available()
    assert is_avail is True

    from akaalEngine.connection.models.endpoint import EndpointSpec
    from akaalEngine.connection.routing.resolver import ResolvedRoute
    from akaalEngine.connection.models.endpoint import RouteType

    spec = EndpointSpec(provider_id="sqlite", database_name=":memory:")
    route = ResolvedRoute(
        effective_host="localhost",
        effective_port=0,
        resolved_ip="127.0.0.1",
        dns_time_ms=0.0,
        route_type=RouteType.DIRECT,
    )

    conn = strategy.connect(spec, route, {})
    assert strategy.validate(conn) is True

    # Perform table creation and verification
    cur = conn.cursor()
    cur.execute("CREATE TABLE live_users (id INT PRIMARY KEY, name TEXT)")
    cur.execute("INSERT INTO live_users VALUES (1, 'Alice')")
    cur.execute("SELECT name FROM live_users WHERE id = 1")
    row = cur.fetchone()
    assert row[0] == "Alice"
    cur.close()

    # Test session reset
    from akaalEngine.connection.models.session import SessionPurpose
    reset_ok = strategy.reset_session(conn, SessionPurpose.BULK_TARGET_WRITE)
    assert reset_ok is True

    strategy.close(conn)
