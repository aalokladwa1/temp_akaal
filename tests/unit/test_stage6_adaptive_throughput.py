"""
Unit tests for Stage 6: Adaptive Throughput Optimizer.
"""

import pytest
from akaal.performance.optimizers.throughput import AdaptiveThroughputOptimizer


def test_adaptive_throughput_optimizer_normal_load():
    optimizer = AdaptiveThroughputOptimizer()
    telemetry = {
        "cpu_percent": 40.0,
        "memory_utilization_pct": 50.0,
        "network_latency_ms": 10.0,
        "target_latency_ms": 15.0,
        "queue_depth": 100,
        "retry_frequency": 0.0,
    }

    spec = optimizer.optimize_throughput(telemetry, {"batch_size": 500, "fetch_size": 1000, "commit_interval_ms": 1000})
    assert spec.batch_size >= 500
    assert spec.fetch_size >= 1000
    assert spec.throttle_delay_sec == 0.0


def test_adaptive_throughput_optimizer_high_pressure():
    optimizer = AdaptiveThroughputOptimizer()
    telemetry = {
        "cpu_percent": 95.0,
        "memory_utilization_pct": 92.0,
        "network_latency_ms": 200.0,
        "target_latency_ms": 300.0,
        "queue_depth": 900,
        "retry_frequency": 0.5,
    }

    spec = optimizer.optimize_throughput(telemetry, {"batch_size": 1000, "fetch_size": 2000, "commit_interval_ms": 2000})
    assert spec.batch_size < 1000
    assert spec.fetch_size < 2000
    assert spec.throttle_delay_sec > 0.0
