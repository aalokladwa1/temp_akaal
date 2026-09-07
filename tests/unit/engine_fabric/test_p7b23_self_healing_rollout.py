"""
P7B.23 -- Self-Healing & Rolling Operations: rollout batch planning + registry-level
fencing hostile scenarios not already covered by test_p7b22_elastic_worker_fabric.py.
"""

import pytest

from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState
from akaalEngine.fabric.worker_fabric.registry import StaleWorkerFencingError, WorkerRegistry
from akaalEngine.fabric.worker_fabric.rollout import RolloutPlanningError, plan_rollout_batch


def _worker(worker_id, version="1.0.0", state=WorkerState.IDLE, epoch=1):
    return WorkerNode(worker_id=worker_id, site_id="site-1", tenant_id="t1", runtime_version=version, state=state, fencing_epoch=epoch)


# ------------------------------------------------------------------ rollout batch planning


def test_no_old_version_workers_rollout_already_complete():
    workers = [_worker("w1", version="2.0.0")]
    plan = plan_rollout_batch(workers, target_version="2.0.0", max_unavailable=1)
    assert plan.is_complete()


def test_batch_respects_max_unavailable():
    workers = [_worker(f"w{i}", version="1.0.0", epoch=i) for i in range(1, 6)]
    plan = plan_rollout_batch(workers, target_version="2.0.0", max_unavailable=2)
    assert len(plan.drain_worker_ids) == 2
    assert plan.remaining_old_version_count == 3


def test_batch_never_breaches_min_available():
    workers = [_worker(f"w{i}", version="1.0.0", epoch=i) for i in range(1, 4)]  # 3 active
    plan = plan_rollout_batch(workers, target_version="2.0.0", max_unavailable=5, min_available=2)
    assert len(plan.drain_worker_ids) == 1  # can only drain 1 (3 - min_available(2))


def test_min_available_equal_to_total_active_drains_nothing():
    workers = [_worker(f"w{i}", version="1.0.0", epoch=i) for i in range(1, 4)]
    plan = plan_rollout_batch(workers, target_version="2.0.0", max_unavailable=5, min_available=3)
    assert plan.drain_worker_ids == ()
    assert plan.remaining_old_version_count == 3


def test_deterministic_selection_lowest_epoch_first():
    workers = [_worker("w-new", version="1.0.0", epoch=5), _worker("w-old", version="1.0.0", epoch=1)]
    plan = plan_rollout_batch(workers, target_version="2.0.0", max_unavailable=1)
    assert plan.drain_worker_ids == ("w-old",)


def test_old_and_new_version_overlap_during_rollout_is_expected_not_an_error():
    """The directive names 'old/new runtime overlap' as a scenario to prove SAFE, not
    forbidden -- this test proves plan_rollout_batch never raises or refuses merely
    because both versions coexist; overlap is the normal mid-rollout state."""
    workers = [_worker("old1", version="1.0.0", epoch=1), _worker("new1", version="2.0.0", epoch=2)]
    plan = plan_rollout_batch(workers, target_version="2.0.0", max_unavailable=1)
    assert plan.drain_worker_ids == ("old1",)  # only the old-version worker is a candidate


def test_revoked_and_stale_workers_excluded_from_rollout_consideration():
    workers = [
        _worker("revoked1", version="1.0.0", state=WorkerState.REVOKED, epoch=1),
        _worker("stale1", version="1.0.0", state=WorkerState.STALE, epoch=2),
        _worker("active1", version="1.0.0", state=WorkerState.IDLE, epoch=3),
    ]
    plan = plan_rollout_batch(workers, target_version="2.0.0", max_unavailable=5)
    assert plan.drain_worker_ids == ("active1",)


def test_empty_target_version_rejected():
    with pytest.raises(RolloutPlanningError):
        plan_rollout_batch([], target_version="", max_unavailable=1)


def test_zero_max_unavailable_rejected():
    with pytest.raises(RolloutPlanningError):
        plan_rollout_batch([], target_version="2.0.0", max_unavailable=0)


def test_negative_min_available_rejected():
    with pytest.raises(RolloutPlanningError):
        plan_rollout_batch([], target_version="2.0.0", max_unavailable=1, min_available=-1)


# ------------------------------------------------------------------ rolling-upgrade fencing (registry-level)


def test_rollback_after_partial_rollout_still_fencing_protected():
    """Rollback (deploying the OLD version again after a partial rollout) must still
    obey strict epoch monotonicity -- a 'rollback' is just another replace_worker call,
    with no special-cased bypass of fencing."""
    reg = WorkerRegistry()
    reg.register(_worker("w1", version="1.0.0", epoch=1))
    reg.replace_worker("w1", _worker("w2", version="2.0.0", epoch=2))
    # Rolling back to 1.0.0 must still present a strictly higher epoch than 2 -- rollback
    # is not a fencing bypass.
    with pytest.raises(StaleWorkerFencingError):
        reg.replace_worker("w2", _worker("w3-rollback", version="1.0.0", epoch=2))
    reg.replace_worker("w2", _worker("w3-rollback", version="1.0.0", epoch=3))  # correctly fenced rollback


def test_failure_mid_rollout_stale_old_worker_reconnecting_is_fenced():
    reg = WorkerRegistry()
    reg.register(_worker("w-old", version="1.0.0", epoch=1))
    reg.replace_worker("w-old", _worker("w-new", version="2.0.0", epoch=2))
    # w-old's process, having been network-partitioned rather than actually dead,
    # reconnects and tries to heartbeat -- must be fenced (REVOKED, terminal).
    with pytest.raises(Exception):
        reg.heartbeat("w-old", "t1")
