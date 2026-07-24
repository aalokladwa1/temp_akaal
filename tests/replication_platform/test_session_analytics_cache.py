"""Tests for Subsystems 4 and 5: Session Manager, Metrics & Analytics, and Multi-Tier Cache."""

import pytest
from akaal.replication.session.manager import ReplicationSessionManager
from akaal.replication.analytics.analytics_engine import AnalyticsEngine, MetricsEngine, CapacityPlanner
from akaal.replication.cache.replication_cache import ReplicationCache


def test_session_manager_lifecycle_checkpoint_lease():
    manager = ReplicationSessionManager()

    session = manager.create_session("sess_101")
    assert session.session_id == "sess_101"

    # Lease acquisition and renewal
    assert manager.lease_mgr.acquire_lease("sess_101", "worker_1") is True
    assert manager.lease_mgr.acquire_lease("sess_101", "worker_2") is False
    assert manager.lease_mgr.renew_lease("sess_101", "worker_1") is True
    manager.lease_mgr.release_lease("sess_101", "worker_1")
    assert manager.lease_mgr.acquire_lease("sess_101", "worker_2") is True

    # Checkpoint saving and retrieving
    manager.checkpoint_mgr.save_checkpoint("sess_101", {"last_row_id": 99500})
    chk = manager.checkpoint_mgr.get_checkpoint("sess_101")
    assert chk is not None
    assert chk["data"]["last_row_id"] == 99500

    # Pause and resume
    manager.coordinator.pause_session(session)
    assert session.state.value == "PAUSED"
    manager.coordinator.resume_session(session)
    assert session.state.value == "IN_PROGRESS"


def test_analytics_and_metrics_engine():
    analytics = AnalyticsEngine()
    analytics.metrics_engine.record_metric("replication_lag_ms", 14.2)
    analytics.metrics_engine.record_metric("throughput_rows_sec", 720000.0)

    report = analytics.generate_analytics_report()
    assert "realtime_metrics" in report
    assert report["realtime_metrics"]["replication_lag_ms"] == 14.2

    forecast = analytics.capacity_planner.forecast_capacity(1000000.0)
    assert forecast["projected_row_rate"] == 1200000.0
    assert forecast["required_workers"] >= 10


def test_replication_cache_operations():
    cache = ReplicationCache()

    cache.set("plan_01", {"status": "CACHED"})
    assert cache.get("plan_01")["status"] == "CACHED"

    cache.set_topology("node_us_east", {"health": 100})
    assert cache.get_topology("node_us_east")["health"] == 100

    cache.set_route("path_01", ["n1", "n2"])
    assert cache.get_route("path_01") == ["n1", "n2"]

    cache.clear()
    assert cache.get("plan_01") is None
