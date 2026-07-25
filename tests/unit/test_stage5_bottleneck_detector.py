"""
Unit tests for Stage 5: Migration Bottleneck Detector.
"""

import pytest
from akaal.operational_reliability.bottleneck_detector import MigrationBottleneckDetector


def test_bottleneck_detector_clean_telemetry():
    detector = MigrationBottleneckDetector()
    telemetry = {
        "lock_wait_time_ms": 10.0,
        "iops_utilization_pct": 30.0,
        "network_latency_ms": 15.0,
        "checkpoint_duration_ms": 200.0,
        "queue_depth": 5,
        "active_workers": 4,
        "memory_utilization_pct": 45.0,
    }

    report = detector.analyze_runtime_telemetry(telemetry)
    assert len(report.bottlenecks) == 0
    assert len(report.recommendations) == 0
    assert report.overall_health_score == 100.0


def test_bottleneck_detector_lock_and_memory_issues():
    detector = MigrationBottleneckDetector()
    telemetry = {
        "lock_wait_time_ms": 250.0,
        "memory_utilization_pct": 90.0,
        "iops_utilization_pct": 92.0,
    }

    report = detector.analyze_runtime_telemetry(telemetry)
    assert len(report.bottlenecks) == 3
    categories = [b.category for b in report.bottlenecks]
    assert "LOCK_CONTENTION" in categories
    assert "MEMORY_PRESSURE" in categories
    assert "IOPS_SATURATION" in categories

    actions = [r.action for r in report.recommendations]
    assert "REDUCE_CONCURRENCY" in actions
    assert "REDUCE_BATCH_SIZE" in actions
    assert report.overall_health_score < 60.0
