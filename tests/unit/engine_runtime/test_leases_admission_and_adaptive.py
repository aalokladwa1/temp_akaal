"""
tests/unit/engine_runtime/test_leases_admission_and_adaptive.py
=================================================================
Unit tests for ExecutionLeaseManager, Fencing Enforcement, ResourceAdmissionController, and AdaptiveConcurrencyController.
"""

import time
import pytest
from akaalEngine.runtime import (
    FencingRejectedError,
    LeaseExpiredError,
    ResourceAdmissionError,
    ResourceBudget,
    ResourceRequirement,
)
from akaalEngine.runtime.leases.manager import ExecutionLeaseManager
from akaalEngine.runtime.resources.adaptive import AdaptiveConcurrencyController
from akaalEngine.runtime.resources.admission import ResourceAdmissionController


def test_lease_manager_acquire_renew_release_and_fencing_epoch():
    """Proves ExecutionLeaseManager acquires, renews, and validates monotonic fencing epochs."""
    mgr = ExecutionLeaseManager(default_ttl_seconds=10.0)

    lease = mgr.acquire_lease(task_id="t1", worker_id="w1", fencing_epoch=1)
    assert lease.fencing_epoch == 1
    assert lease.is_expired is False
    assert mgr.validate_lease(lease.lease_id, fencing_epoch=1) is True

    # Renew
    renewed = mgr.renew_lease(lease.lease_id, ttl_seconds=20.0)
    assert renewed.expires_at > lease.expires_at

    # Attempt acquiring with lower fencing epoch -> FencingRejectedError
    with pytest.raises(FencingRejectedError) as exc_info:
        mgr.acquire_lease(task_id="t1", worker_id="w2", fencing_epoch=0)
    assert exc_info.value.details["active_epoch"] == 1
    assert exc_info.value.details["attempted_epoch"] == 0

    # Higher fencing epoch advances epoch
    lease2 = mgr.acquire_lease(task_id="t1", worker_id="w2", fencing_epoch=2)
    assert lease2.fencing_epoch == 2
    # Old lease with epoch 1 is now invalid for fencing
    assert mgr.validate_lease(lease.lease_id, fencing_epoch=1) is False

    mgr.release_lease(lease2.lease_id)


def test_resource_admission_controller_enforces_capacity():
    """Proves ResourceAdmissionController admits work under capacity and rejects oversubscribed requests."""
    budget = ResourceBudget(max_worker_slots=2, max_cpu_cores=4.0, max_memory_mb=1024.0)
    ctrl = ResourceAdmissionController(budget=budget)

    req1 = ResourceRequirement(cpu_cores=2.0, memory_mb=512.0, concurrency_slots=1)
    ctrl.allocate(req1)

    req2 = ResourceRequirement(cpu_cores=2.0, memory_mb=512.0, concurrency_slots=1)
    ctrl.allocate(req2)

    # 3rd allocation exceeds slots limit -> ResourceAdmissionError
    req3 = ResourceRequirement(cpu_cores=1.0, memory_mb=128.0, concurrency_slots=1)
    with pytest.raises(ResourceAdmissionError) as exc_info:
        ctrl.allocate(req3)
    assert "slots exhausted" in str(exc_info.value)

    ctrl.release(req1)
    # Now req3 can be admitted
    ctrl.allocate(req3)


def test_adaptive_concurrency_controller_aimd_autoscale():
    """Proves AdaptiveConcurrencyController scales worker bounds based on CPU, RAM, and queue metrics."""
    ctrl = AdaptiveConcurrencyController(min_workers=2, max_workers=10)
    assert ctrl.current_workers == 2

    # Headroom available + queue depth -> Scale UP
    metrics_up = {"cpu_percent": 40.0, "memory_utilization_pct": 50.0, "queue_depth": 20}
    dec1 = ctrl.evaluate(metrics_up)
    assert dec1.scaling_direction == "UP"
    assert dec1.recommended_workers == 3

    # High CPU pressure -> Scale DOWN (Multiplicative decrease)
    metrics_down = {"cpu_percent": 95.0, "memory_utilization_pct": 50.0, "queue_depth": 0}
    dec2 = ctrl.evaluate(metrics_down)
    assert dec2.scaling_direction == "DOWN"
    assert dec2.recommended_workers < 3
