"""
P7B.22 -- Elastic Worker Fabric: positive, hostile, and cross-tenant tests.
"""

import pytest

from akaalEngine.fabric.worker_fabric.models import WorkerCapacity, WorkerNode, WorkerState, WorkerValidationError
from akaalEngine.fabric.worker_fabric.registry import (
    DuplicateWorkerIdentityError,
    StaleWorkerFencingError,
    UnknownWorkerError,
    WorkerRegistrationError,
    WorkerRegistry,
)
from akaalEngine.fabric.worker_fabric.scaling import ScaleAction, ScalingPolicyError, recommend_scale_action


def _worker(worker_id, site="site-1", tenant="t1", epoch=1, state=WorkerState.IDLE):
    return WorkerNode(worker_id=worker_id, site_id=site, tenant_id=tenant, runtime_version="1.0.0",
                       capabilities=frozenset({"oracle"}), capability_provenance="worker-registration",
                       fencing_epoch=epoch, state=state)


# ------------------------------------------------------------------ positive


def test_register_and_get_roundtrip():
    reg = WorkerRegistry()
    reg.register(_worker("w1"))
    got = reg.get("w1", "t1")
    assert got.worker_id == "w1"
    assert got.is_schedulable()


def test_heartbeat_updates_capacity_and_timestamp():
    reg = WorkerRegistry()
    reg.register(_worker("w1"))
    cap = WorkerCapacity(cpu_cores=8, memory_mb=32000, provenance="worker-heartbeat")
    updated = reg.heartbeat("w1", "t1", capacity=cap)
    assert updated.capacity.cpu_cores == 8


def test_drain_then_cannot_be_scheduled():
    reg = WorkerRegistry()
    reg.register(_worker("w1"))
    reg.request_drain("w1", "t1")
    w = reg.get("w1", "t1")
    assert not w.is_schedulable()
    assert w.is_active()  # still active (allowed to finish existing work), just not schedulable for NEW work


# ------------------------------------------------------------------ hostile: fencing / self-healing (P7B.23)


def test_replacement_with_higher_epoch_accepted_and_old_revoked():
    reg = WorkerRegistry()
    reg.register(_worker("w1", epoch=1))
    reg.replace_worker("w1", _worker("w2", epoch=2))
    assert reg.get("w2", "t1").state == WorkerState.IDLE
    assert reg.get("w1", "t1").state == WorkerState.REVOKED


def test_replacement_with_equal_or_lower_epoch_rejected():
    reg = WorkerRegistry()
    reg.register(_worker("w1", epoch=5))
    with pytest.raises(StaleWorkerFencingError):
        reg.replace_worker("w1", _worker("w2", epoch=5))
    with pytest.raises(StaleWorkerFencingError):
        reg.replace_worker("w1", _worker("w3", epoch=3))


def test_stale_worker_cannot_heartbeat_after_revocation():
    """Old worker returning after replacement (crash/restart race) must be fenced."""
    reg = WorkerRegistry()
    reg.register(_worker("w1", epoch=1))
    reg.replace_worker("w1", _worker("w2", epoch=2))
    with pytest.raises(WorkerRegistrationError):
        reg.heartbeat("w1", "t1")  # revoked worker cannot heartbeat back to life


def test_duplicate_worker_registration_same_epoch_rejected_not_silently_merged():
    """Two workers claiming the same assignment slot: only the strictly-higher epoch wins."""
    reg = WorkerRegistry()
    reg.register(_worker("w1", epoch=1))
    with pytest.raises(StaleWorkerFencingError):
        reg.register(_worker("w2", epoch=1))  # same epoch, different worker_id -- refused


def test_old_worker_returning_with_stale_epoch_after_rolling_upgrade_rejected():
    reg = WorkerRegistry()
    reg.register(_worker("w-old", epoch=10))
    reg.replace_worker("w-old", _worker("w-new", epoch=11))
    # w-old crashes and restarts, tries to re-register with its original epoch:
    with pytest.raises(StaleWorkerFencingError):
        reg.register(_worker("w-old-restarted", epoch=10))


def test_worker_id_collision_different_site_rejected():
    reg = WorkerRegistry()
    reg.register(_worker("w1", site="site-a"))
    with pytest.raises(DuplicateWorkerIdentityError):
        reg.register(_worker("w1", site="site-b", epoch=99))


def test_revoked_worker_state_is_terminal():
    reg = WorkerRegistry()
    reg.register(_worker("w1"))
    reg.revoke("w1", "t1")
    with pytest.raises(WorkerRegistrationError):
        reg.request_drain("w1", "t1")


# ------------------------------------------------------------------ hostile: cross-tenant


def test_cross_tenant_get_never_leaks_existence():
    """Because the registry key is (tenant_id, worker_id), a wrong-tenant lookup finds
    nothing at all -- UnknownWorkerError, never a tenant-mismatch error that would
    confirm the worker_id exists under some OTHER tenant. This is the stronger of the two
    properties (no existence leak)."""
    reg = WorkerRegistry()
    reg.register(_worker("w1", tenant="t1"))
    with pytest.raises(UnknownWorkerError):
        reg.get("w1", "t2-attacker")


def test_cross_tenant_heartbeat_never_leaks_existence():
    reg = WorkerRegistry()
    reg.register(_worker("w1", tenant="t1"))
    with pytest.raises(UnknownWorkerError):
        reg.heartbeat("w1", "t2-attacker")


def test_same_worker_id_different_tenants_isolated():
    reg = WorkerRegistry()
    reg.register(_worker("shared-id", tenant="t1", site="site-x"))
    reg.register(_worker("shared-id", tenant="t2", site="site-y"))
    assert reg.get("shared-id", "t1").site_id == "site-x"
    assert reg.get("shared-id", "t2").site_id == "site-y"


def test_unknown_worker_raises_not_fabricated():
    reg = WorkerRegistry()
    with pytest.raises(UnknownWorkerError):
        reg.get("nope", "t1")


# ------------------------------------------------------------------ hostile: malformed input


def test_negative_capacity_rejected_at_construction():
    with pytest.raises(WorkerValidationError):
        WorkerCapacity(cpu_cores=-1, provenance="worker-heartbeat")


def test_empty_worker_id_rejected():
    with pytest.raises(WorkerValidationError):
        WorkerNode(worker_id="", site_id="s1", tenant_id="t1", runtime_version="1.0.0")


def test_fencing_epoch_below_one_rejected():
    with pytest.raises(WorkerValidationError):
        WorkerNode(worker_id="w1", site_id="s1", tenant_id="t1", runtime_version="1.0.0", fencing_epoch=0)


# ------------------------------------------------------------------ scaling signals (P7B.22)


def test_zero_workers_with_backlog_recommends_scale_out():
    rec = recommend_scale_action([], queued_assignments=10)
    assert rec.action == ScaleAction.SCALE_OUT


def test_zero_workers_zero_backlog_holds():
    rec = recommend_scale_action([], queued_assignments=0)
    assert rec.action == ScaleAction.HOLD


def test_high_backlog_ratio_recommends_scale_out():
    workers = [_worker(f"w{i}", state=WorkerState.BUSY) for i in range(2)]
    rec = recommend_scale_action(workers, queued_assignments=20, max_backlog_per_worker=2.0)
    assert rec.action == ScaleAction.SCALE_OUT


def test_excess_idle_workers_recommends_scale_in():
    workers = [_worker(f"w{i}") for i in range(10)]  # all idle
    rec = recommend_scale_action(workers, queued_assignments=0, max_idle_workers=3, min_idle_workers=1)
    assert rec.action == ScaleAction.SCALE_IN


def test_within_thresholds_holds():
    workers = [_worker("w1"), _worker("w2", state=WorkerState.BUSY)]
    rec = recommend_scale_action(workers, queued_assignments=1, max_backlog_per_worker=5.0, min_idle_workers=1, max_idle_workers=5)
    assert rec.action == ScaleAction.HOLD


def test_negative_backlog_rejected():
    with pytest.raises(ScalingPolicyError):
        recommend_scale_action([], queued_assignments=-1)


def test_single_worker_dominant_metrics_do_not_bypass_aggregate_logic():
    """A single worker's state cannot manufacture a scale decision inconsistent with the
    whole fleet's aggregate -- proven by constructing a fleet where one worker is BUSY
    (i.e., 'wants attention') but the aggregate backlog ratio is still low."""
    workers = [_worker(f"w{i}", state=WorkerState.IDLE) for i in range(9)] + [_worker("w-busy", state=WorkerState.BUSY)]
    rec = recommend_scale_action(workers, queued_assignments=1, max_backlog_per_worker=5.0, max_idle_workers=20)
    assert rec.action == ScaleAction.HOLD
