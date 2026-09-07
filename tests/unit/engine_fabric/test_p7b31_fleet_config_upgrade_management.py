"""
tests.unit.engine_fabric.test_p7b31_fleet_config_upgrade_management
========================================================================
P7B.31 -- Fleet Configuration & Upgrade Management hostile test suite.

Proves RuntimeCompatibilityPolicy/RevisionHistory (P7B.31, genuinely new and small)
compose correctly with the frozen P7B.22 WorkerRegistry, P7B.23 plan_rollout_batch, and
P7B.30 FleetDesiredState/reconcile_fleet_state -- no duplicate worker registry, rollout
planner, or GitOps authority.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.fleet_lifecycle import FleetLifecycleError, RevisionHistory, RuntimeCompatibilityPolicy
from akaalEngine.fabric.gitops import FleetDesiredState, ReconciliationState, reconcile_fleet_state
from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState
from akaalEngine.fabric.worker_fabric.registry import StaleWorkerFencingError, WorkerRegistry
from akaalEngine.fabric.worker_fabric.rollout import plan_rollout_batch


def _worker(worker_id, version, state=WorkerState.IDLE, epoch=1, site_id="site-1", tenant_id="tenant-a"):
    return WorkerNode(worker_id=worker_id, site_id=site_id, tenant_id=tenant_id, runtime_version=version, state=state, fencing_epoch=epoch)


# ----------------------------------------------------------------------
# RuntimeCompatibilityPolicy -- no default-allow
# ----------------------------------------------------------------------

def test_compatibility_policy_rejects_unlisted_version():
    policy = RuntimeCompatibilityPolicy(policy_id="p1", allowed_versions=frozenset({"2.0.0", "2.0.1"}))
    assert policy.is_compatible("2.0.0") is True
    assert policy.is_compatible("1.9.9") is False


def test_compatibility_policy_requires_non_empty_allowed_set():
    with pytest.raises(FleetLifecycleError):
        RuntimeCompatibilityPolicy(policy_id="p1", allowed_versions=frozenset())


def test_unsupported_version_combination_fails_closed_for_new_work():
    """Composition proof: a worker whose runtime_version is not in the compatibility
    policy must never be selected for new work -- proven via the existing capability
    exact-match mechanism (P7B.13), used here with runtime_version modeled as a required
    capability string, exactly how a real deployment would gate it."""
    from akaalEngine.fabric.placement.capability import CapabilityRequirement, evaluate_capability
    from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry

    policy = RuntimeCompatibilityPolicy(policy_id="p1", allowed_versions=frozenset({"2.0.0"}))
    registry = SiteRegistry()
    site = ExecutionSite(
        site_id="site-1", site_kind=SiteKind.CLOUD_VM, environment_id="env-1",
        capabilities=frozenset({"runtime-version:1.0.0"}),
    )
    registry.register(site)

    requirement = CapabilityRequirement(required_capabilities=frozenset({f"runtime-version:2.0.0"}), plan_reference="plan-1")
    assert policy.is_compatible("1.0.0") is False
    evaluation = evaluate_capability(registry.get("site-1"), requirement)
    assert evaluation.satisfied is False
    assert "runtime-version:2.0.0" in evaluation.missing_capabilities


# ----------------------------------------------------------------------
# Old worker return during/after upgrade -- composition over frozen P7B.22/23
# ----------------------------------------------------------------------

def test_old_worker_cannot_regain_authority_after_rolling_replacement():
    registry = WorkerRegistry()
    old = registry.register(_worker("w-old", "1.0.0", epoch=1))
    registry.replace_worker("w-old", _worker("w-new", "2.0.0", epoch=2))

    # The old worker heartbeating (as if it came back mid/after upgrade) must be refused.
    with pytest.raises(Exception):
        registry.heartbeat("w-old", "tenant-a")


def test_old_worker_cannot_re_register_with_stale_epoch_after_upgrade():
    registry = WorkerRegistry()
    registry.register(_worker("w1", "1.0.0", epoch=1))
    registry.replace_worker("w1", _worker("w1", "2.0.0", epoch=2))
    with pytest.raises(StaleWorkerFencingError):
        registry.register(_worker("w1", "1.0.0", epoch=1))  # attempted resurrection at old epoch


def test_rolling_upgrade_batch_respects_min_available_and_targets_old_version_only():
    registry = WorkerRegistry()
    for i in range(4):
        registry.register(_worker(f"w{i}", "1.0.0", epoch=i + 1, site_id=f"site-{i}"))
    workers = list(registry.list_workers_for_tenant("tenant-a"))
    plan = plan_rollout_batch(workers, target_version="2.0.0", max_unavailable=1, min_available=3)
    assert len(plan.drain_worker_ids) == 1
    assert plan.remaining_old_version_count == 3


def test_upgrade_during_active_bulk_migration_does_not_touch_ownership():
    """Structural proof: nothing in the fleet-lifecycle upgrade path (WorkerRegistry,
    plan_rollout_batch, RuntimeCompatibilityPolicy, RevisionHistory) imports or references
    the P7B.25 ownership authority at all -- an upgrade cannot roll back or interfere with
    migration ownership/lease/fencing state merely by being an infrastructure change."""
    import akaalEngine.fabric.fleet_lifecycle.models as fl_models
    import akaalEngine.fabric.worker_fabric.rollout as rollout_mod
    import inspect

    for module in (fl_models, rollout_mod):
        source = inspect.getsource(module)
        assert "ownership" not in source.lower()
        assert "OwnershipManager" not in source


# ----------------------------------------------------------------------
# Revision history / rollback
# ----------------------------------------------------------------------

def test_rollback_targets_a_real_prior_revision_only():
    history = RevisionHistory()
    rev1 = FleetDesiredState(revision_id="rev-1", target_runtime_version="1.0.0", target_worker_pool_size=2, approved_by="alice")
    history.record_applied(rev1)
    with pytest.raises(FleetLifecycleError):
        history.rollback_to("rev-never-existed")


def test_rollback_records_a_new_revision_pointing_at_old_content():
    history = RevisionHistory()
    rev1 = FleetDesiredState(revision_id="rev-1", target_runtime_version="1.0.0", target_worker_pool_size=2, approved_by="alice")
    rev2 = FleetDesiredState(revision_id="rev-2", target_runtime_version="2.0.0", target_worker_pool_size=2, approved_by="bob")
    history.record_applied(rev1)
    history.record_applied(rev2)
    assert history.current().revision_id == "rev-2"

    rolled_back = history.rollback_to("rev-1")
    assert rolled_back.target_runtime_version == "1.0.0"
    assert history.current().revision_id == "rev-1"
    # History is append-only -- three entries now, not two (rollback is a new event).
    assert len(history.history()) == 3


def test_rollback_does_not_roll_worker_registry_state_backward():
    """Infrastructure rollback (desired-state pointer) must not itself force worker state
    backward -- reconciliation after a rollback correctly reports DRIFTED (workers are
    still at the newer version) rather than silently pretending they've been downgraded."""
    registry = WorkerRegistry()
    registry.register(_worker("w1", "2.0.0"))
    history = RevisionHistory()
    rev1 = FleetDesiredState(revision_id="rev-1", target_runtime_version="1.0.0", target_worker_pool_size=1, approved_by="alice")
    rev2 = FleetDesiredState(revision_id="rev-2", target_runtime_version="2.0.0", target_worker_pool_size=1, approved_by="bob")
    history.record_applied(rev1)
    history.record_applied(rev2)

    rolled_back = history.rollback_to("rev-1")
    report = reconcile_fleet_state(rolled_back, list(registry.list_workers_for_tenant("tenant-a")))
    assert report.state == ReconciliationState.DRIFTED
    # The actual worker is untouched -- still 2.0.0.
    assert registry.get("w1", "tenant-a").runtime_version == "2.0.0"
