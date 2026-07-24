"""Tests for Resilience Mechanisms and Reliability Schedulers."""

import pytest
from akaal.reliability.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    BulkheadIsolationManager,
    AdaptiveLoadShedder,
    IntelligentRetryEngine,
)
from akaal.reliability.scheduler.recovery_scheduler import (
    ReliabilityRetryScheduler,
    ReliabilityRecoveryScheduler,
    MaintenanceWindowScheduler,
)


def test_circuit_breaker_lifecycle():
    cb = CircuitBreaker("db_breaker", failure_threshold=2, reset_timeout_sec=0.1)
    assert cb.can_execute() is True

    cb.record_failure()
    cb.record_failure()
    assert cb.can_execute() is False

    cb.record_success()
    cb.state = CircuitState.CLOSED
    assert cb.can_execute() is True


def test_bulkhead_concurrency():
    mgr = BulkheadIsolationManager(max_concurrent_calls=1)
    res1 = mgr.execute_in_bulkhead(lambda: "OK")
    assert res1["status"] == "SUCCESS"


def test_adaptive_load_shedder():
    shedder = AdaptiveLoadShedder()
    assert shedder.should_shed_request("Low", 92.0) is True
    assert shedder.should_shed_request("Critical", 92.0) is False


def test_intelligent_retry_engine():
    retry_engine = IntelligentRetryEngine()
    counter = 0

    def failing_fn():
        nonlocal counter
        counter += 1
        if counter < 2:
            raise ValueError("Transient error")
        return "SUCCESS"

    res = retry_engine.execute_with_retry(failing_fn, max_retries=3)
    assert res["status"] == "SUCCESS"
    assert res["attempts"] == 2


def test_schedulers():
    retry_sched = ReliabilityRetryScheduler()
    task = retry_sched.schedule_retry("task_01", attempt=2, payload={"service": "auth"})
    assert task.task_type == "RETRY"

    rec_sched = ReliabilityRecoveryScheduler()
    rec_sched.enqueue_recovery("service_a", priority=1)
    popped = rec_sched.pop_next_recovery()
    assert popped is not None
    assert popped.task_id == "service_a"
