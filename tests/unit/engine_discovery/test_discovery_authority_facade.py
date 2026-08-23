"""
Unit tests for DiscoveryAuthority facade, caching, drift detection, and session lifecycle.
"""

import sqlite3
import pytest
from akaalEngine.connection.models.endpoint import AuthenticationSpec, AuthenticationType, EndpointSpec
from akaalEngine.discovery.authority import DiscoveryAuthority
from akaalEngine.discovery.models.context import DiscoveryContext, DiscoveryDepth, DiscoveryScope
from akaalEngine.discovery.models.snapshot import DiscoveryCompleteness


@pytest.fixture
def sqlite_in_memory_db(tmp_path):
    db_file = str(tmp_path / "test_discovery.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT)")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, FOREIGN KEY(customer_id) REFERENCES customers(id))")
    conn.execute("CREATE INDEX idx_orders_customer ON orders(customer_id)")
    conn.execute("INSERT INTO customers VALUES (1, 'Alice', 'alice@example.com'), (2, 'Bob', 'bob@example.com')")
    conn.execute("INSERT INTO orders VALUES (101, 1, 99.5), (102, 1, 149.0)")
    conn.commit()
    conn.close()
    return db_file


def test_discovery_sqlite_end_to_end(sqlite_in_memory_db):
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=sqlite_in_memory_db,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )

    auth = DiscoveryAuthority()
    ctx = DiscoveryContext(depth=DiscoveryDepth.STANDARD, allow_exact_counts=True)
    snapshot = auth.discover(spec, context=ctx, use_cache=False)

    assert snapshot.completeness == DiscoveryCompleteness.FULL
    assert snapshot.engine_identity is not None
    assert snapshot.engine_identity.provider_id == "sqlite"
    assert snapshot.namespaces is not None
    assert "main" in snapshot.namespaces.schemas
    assert snapshot.objects is not None

    table_names = [t.name for t in snapshot.objects.tables]
    assert "customers" in table_names
    assert "orders" in table_names

    # Check structure
    assert "main.orders" in snapshot.structures
    orders_struct = snapshot.structures["main.orders"]
    col_names = [c.name for c in orders_struct.columns]
    assert "id" in col_names
    assert "customer_id" in col_names
    assert "amount" in col_names
    assert len(orders_struct.foreign_keys) == 1
    assert orders_struct.foreign_keys[0].referenced_table == "customers"


def test_discovery_caching_and_invalidation(sqlite_in_memory_db):
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=sqlite_in_memory_db,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )

    auth = DiscoveryAuthority()
    snap1 = auth.discover(spec, use_cache=True)
    snap2 = auth.discover(spec, use_cache=True)
    assert snap1 is snap2  # Cached exact reference

    # Invalidate
    auth.invalidate_cache(spec)
    snap3 = auth.discover(spec, use_cache=True)
    assert snap3 is not snap1
    assert snap3.snapshot_id != snap1.snapshot_id


def test_discovery_drift_detection(sqlite_in_memory_db):
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=sqlite_in_memory_db,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )

    auth = DiscoveryAuthority()
    baseline = auth.discover(spec, use_cache=False)

    # Modify live schema
    conn = sqlite3.connect(sqlite_in_memory_db)
    conn.execute("CREATE TABLE shipments (id INTEGER PRIMARY KEY, status TEXT)")
    conn.commit()
    conn.close()

    drift_report = auth.detect_drift(baseline, spec)
    assert drift_report.is_drifted is True
    assert len(drift_report.change_summary) > 0


def test_discovery_preview_sampling(sqlite_in_memory_db):
    spec = EndpointSpec(
        provider_id="sqlite",
        database_name=sqlite_in_memory_db,
        auth_spec=AuthenticationSpec(auth_type=AuthenticationType.NONE),
    )

    auth = DiscoveryAuthority()
    sample = auth.sample(spec, "main", "customers", limit=5)
    assert sample.table_name == "customers"
    assert sample.sample_count == 2
    assert sample.is_sampled is True
    assert sample.is_redacted is True
    assert len(sample.records) == 2
    assert sample.records[0]["name"] == "Alice"
