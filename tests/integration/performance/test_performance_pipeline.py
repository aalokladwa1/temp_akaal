import pytest
from akaal.performance.facade.runtime import DefaultPerformanceRuntimeV1
from akaal.performance.orchestration.optimization_session import OptimizationState
from akaal.performance.failures.classification import PerformanceEngineError


def test_optimization_session_state_transitions():
    runtime = DefaultPerformanceRuntimeV1()
    
    # 1. Run automatic cycle
    session = runtime.trigger_optimization_cycle(mode="Auto")
    assert session.current_state == OptimizationState.COMPLETED
    assert session.session_id in runtime.session_manager._sessions

    # Verify state history
    states = [h["state"] for h in session.state_history]
    assert OptimizationState.CREATED in states
    assert OptimizationState.BASELINE_CAPTURED in states
    assert OptimizationState.ANALYZING in states
    assert OptimizationState.RULES_EVALUATED in states
    assert OptimizationState.COMPLETED in states


def test_safe_mode_approval_lifecycle():
    runtime = DefaultPerformanceRuntimeV1()
    runtime.set_mock_metrics("queue_depth", 150)  # trigger rule

    # 1. Trigger safe mode
    session = runtime.trigger_optimization_cycle(mode="Safe")
    assert session.current_state == OptimizationState.WAITING_APPROVAL

    # 2. Approve recommendations
    runtime.pipeline.approve_recommendation(session.session_id)
    assert session.current_state == OptimizationState.COMPLETED
    assert runtime.get_active_configuration()["worker_count"] == 8


def test_automatic_rollback_on_degradation():
    runtime = DefaultPerformanceRuntimeV1()
    
    # Set high latency in mock telemetry before op cycle
    runtime.set_mock_metrics("latency_ms", 25.0)
    runtime.set_mock_metrics("queue_depth", 150)  # triggers rule to change config to worker_count: 8

    # Force post-optimization latency spike to trigger validation failure
    call_count = 0
    def degrade_on_exec():
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            runtime.set_mock_metrics("latency_ms", 85.0)  # Post-op degradation
        return runtime._mock_metrics

    runtime.pipeline.get_metrics_cb = degrade_on_exec

    # Trigger cycle
    session = runtime.trigger_optimization_cycle(mode="Auto")
    
    # Validation failed, rollback executed
    assert session.current_state == OptimizationState.ROLLED_BACK
    assert len(session.rollback_events) == 1
    # Verify config restored back to original baseline (worker_count = 4)
    assert runtime.get_active_configuration()["worker_count"] == 4
