"""tests/unit/engine_intelligence/test_p7c14_health_sample_store.py
=======================================================================
P7C.14 HealthSampleStore: bounded retention (never unbounded growth),
tenant/migration scoping, oldest-first ordering for trend math.
"""

from __future__ import annotations

import sqlite3

import pytest

from akaalEngine.intelligence.anomaly.store import HealthSample, HealthSampleStore


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    store = HealthSampleStore()
    store.ensure_table(connection)
    yield connection
    connection.close()


class TestBoundedRetention:
    def test_retention_cap_enforced_never_unbounded(self, conn, monkeypatch):
        store = HealthSampleStore()
        monkeypatch.setattr(HealthSampleStore, "MAX_SAMPLES_PER_MIGRATION", 5)
        for i in range(20):
            store.save(HealthSample.new(tenant_id="t1", migration_id="m1", dimensions={"i": i}), conn)
            conn.commit()
        cur = conn.execute("SELECT COUNT(*) FROM intelligence_health_samples WHERE tenant_id='t1' AND migration_id='m1'")
        assert cur.fetchone()[0] == 5

    def test_retention_keeps_most_recent(self, conn, monkeypatch):
        store = HealthSampleStore()
        monkeypatch.setattr(HealthSampleStore, "MAX_SAMPLES_PER_MIGRATION", 3)
        for i in range(10):
            store.save(HealthSample.new(tenant_id="t1", migration_id="m1", dimensions={"i": i}, observed_at=f"2024-01-01T00:00:{i:02d}+00:00"), conn)
        conn.commit()
        recent = store.list_recent("t1", "m1", conn, limit=10)
        assert [s.dimensions["i"] for s in recent] == [7, 8, 9]


class TestScopingAndOrdering:
    def test_different_migrations_do_not_share_history(self, conn):
        store = HealthSampleStore()
        store.save(HealthSample.new(tenant_id="t1", migration_id="m1", dimensions={"x": 1}), conn)
        store.save(HealthSample.new(tenant_id="t1", migration_id="m2", dimensions={"x": 2}), conn)
        conn.commit()
        m1_samples = store.list_recent("t1", "m1", conn)
        assert len(m1_samples) == 1 and m1_samples[0].dimensions["x"] == 1

    def test_oldest_first_ordering(self, conn):
        store = HealthSampleStore()
        for i, ts in enumerate(["2024-01-01T00:00:03+00:00", "2024-01-01T00:00:01+00:00", "2024-01-01T00:00:02+00:00"]):
            store.save(HealthSample.new(tenant_id="t1", migration_id="m1", dimensions={"i": i}, observed_at=ts), conn)
        conn.commit()
        samples = store.list_recent("t1", "m1", conn)
        assert [s.observed_at for s in samples] == sorted(s.observed_at for s in samples)
