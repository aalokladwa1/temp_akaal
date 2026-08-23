"""
tests/unit/engine_telemetry/test_metrics_cardinality_and_prometheus.py
========================================================================
Unit tests for MetricsRegistry, Histograms, CardinalityGuard, and Prometheus text exporter.
"""

import pytest
from akaalEngine.telemetry import TelemetryAuthority
from akaalEngine.telemetry.metrics.cardinality import CardinalityGuard
from akaalEngine.telemetry.metrics.registry import MetricsRegistry


def test_metrics_registry_counters_gauges_histograms_and_timers():
    """Proves MetricsRegistry records counters, gauges, histograms (real percentiles), and timers."""
    reg = MetricsRegistry()

    reg.record_counter("tasks_completed_total", increment=1.0, labels={"type": "bulk"})
    reg.record_counter("tasks_completed_total", increment=2.0, labels={"type": "bulk"})
    reg.set_gauge("memory_utilization_pct", 75.5)

    for val in range(1, 101):
        reg.observe_histogram("task_duration_seconds", float(val))

    reg.observe_timer("checkpoint_save_seconds", 0.5)
    reg.observe_timer("checkpoint_save_seconds", 1.5)

    snap = reg.get_snapshot()

    # Counter
    assert snap.counters['tasks_completed_total{type="bulk"}'] == 3.0

    # Gauge
    assert snap.gauges["memory_utilization_pct"] == 75.5

    # Histogram P50, P95, P99
    hist = snap.histograms["task_duration_seconds"]
    assert hist["count"] == 100.0
    assert hist["p50"] == 50.5
    assert hist["p95"] == 95.05
    assert hist["p99"] == 99.01

    # Timer
    timer = snap.rate_timers["checkpoint_save_seconds"]
    assert timer["count"] == 2.0
    assert timer["total_seconds"] == 2.0
    assert timer["avg_seconds"] == 1.0


def test_cardinality_guard_filters_forbidden_dynamic_labels():
    """Proves CardinalityGuard strips dynamic identifier keys (row_id, task_id, etc.) from metric labels."""
    guard = CardinalityGuard(max_cardinality_per_metric=5)

    raw_labels = {"provider": "postgresql", "task_id": "t-12345", "chunk_id": "c-999"}
    safe = guard.filter_labels(raw_labels)

    assert "provider" in safe
    assert "task_id" not in safe
    assert "chunk_id" not in safe


def test_prometheus_text_exporter_format():
    """Proves PrometheusTextExporter produces standard valid Prometheus exposition text."""
    telemetry = TelemetryAuthority()
    telemetry.record_counter("http_requests_total", 5.0, labels={"method": "GET"})
    telemetry.set_gauge("active_workers_count", 4.0)

    text = telemetry.export_prometheus_text()
    assert "# TYPE http_requests_total counter" in text
    assert 'http_requests_total{method="GET"} 5.0' in text
    assert "# TYPE active_workers_count gauge" in text
    assert "active_workers_count 4.0" in text
