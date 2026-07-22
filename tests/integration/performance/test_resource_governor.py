"""
Integration Tests for Resource Governor and Atomic Hot Reload.
"""

import pytest
from akaal.performance.facade.runtime import DefaultPerformanceRuntimeV1
from akaal.performance.failures.classification import PerformanceEngineError, PerformanceFailureType


def test_resource_governor_limit_violations():
    runtime = DefaultPerformanceRuntimeV1()

    # Enforce CPU limit: requested 95%, limit is 90%
    with pytest.raises(PerformanceEngineError) as exc:
        runtime.governor.enforce_cpu(95.0)
    assert exc.value.failure_type == PerformanceFailureType.LIMIT_EXCEEDED

    # Enforce concurrency limit: requested 24, limit is 16
    with pytest.raises(PerformanceEngineError) as exc:
        runtime.governor.enforce_concurrency(24)
    assert exc.value.failure_type == PerformanceFailureType.LIMIT_EXCEEDED


def test_atomic_config_hot_reload():
    runtime = DefaultPerformanceRuntimeV1()
    current = runtime.get_active_configuration()
    assert current["worker_count"] == 4

    # 1. Successful hot reload
    update_cfg = dict(current)
    update_cfg["worker_count"] = 6
    runtime.apply_runtime_configuration(update_cfg)
    assert runtime.get_active_configuration()["worker_count"] == 6

    # 2. Failed hot reload (invalid value rejects update)
    invalid_cfg = dict(current)
    invalid_cfg["limits"]["cpu_percent"] = 120.0  # violates compatibility bounds
    
    with pytest.raises(PerformanceEngineError) as exc:
        runtime.apply_runtime_configuration(invalid_cfg)
    
    assert exc.value.failure_type == PerformanceFailureType.CONFIGURATION
    # Active value was not affected
    assert runtime.get_active_configuration()["limits"]["cpu_percent"] == current["limits"]["cpu_percent"]
