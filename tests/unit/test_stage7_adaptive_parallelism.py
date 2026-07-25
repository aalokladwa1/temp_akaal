"""
Unit tests for Stage 7: Adaptive Parallelism Engine.
"""

import pytest
from akaal.performance.optimizers.adaptive_parallelism import AdaptiveParallelismEngine


def test_adaptive_parallelism_upscale():
    engine = AdaptiveParallelismEngine()
    telemetry = {
        "cpu_percent": 45.0,
        "memory_utilization_pct": 50.0,
        "connection_pool_utilization_pct": 60.0,
        "lock_wait_time_ms": 5.0,
        "worker_utilization_pct": 85.0,
        "queue_depth": 120,
    }

    decision = engine.autoscale_workers(telemetry, current_workers=4)
    assert decision.is_scaling_event is True
    assert decision.scaling_direction == "UP"
    assert decision.recommended_workers == 5
    assert decision.parallel_chunks == 10


def test_adaptive_parallelism_downscale_on_cpu_pressure():
    engine = AdaptiveParallelismEngine()
    telemetry = {
        "cpu_percent": 92.0,
        "memory_utilization_pct": 50.0,
        "connection_pool_utilization_pct": 60.0,
        "lock_wait_time_ms": 5.0,
    }

    decision = engine.autoscale_workers(telemetry, current_workers=6)
    assert decision.is_scaling_event is True
    assert decision.scaling_direction == "DOWN"
    assert decision.recommended_workers == 5
    assert "CPU pressure elevated" in decision.reason
