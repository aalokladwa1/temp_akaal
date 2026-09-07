"""
tests.unit.engine_fabric.test_p7b30_gitops_fleet_lifecycle
===============================================================
P7B.30 -- GitOps & Fleet Lifecycle hostile test suite.

Proves FleetDesiredState/reconcile_fleet_state (composed over the frozen P7B.22
WorkerRegistry/WorkerNode -- no duplicate fleet authority) enforce:
    * GitOps desired state structurally cannot carry secrets or live migration/ownership/
      fencing truth (no field exists for it; the one open config field is additionally
      scanned)
    * every revision is attributable (non-empty approved_by)
    * reconciliation state (IN_SYNC/PENDING/DRIFTED/INCOMPATIBLE/PARTIALLY_APPLIED)
      reflects actual worker state, never wishful thinking
    * compatibility is judged only by the caller-supplied callback, never assumed
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.gitops import FleetDesiredState, GitOpsValidationError, ReconciliationState, reconcile_fleet_state
from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState


def _worker(worker_id, version, state=WorkerState.IDLE, tenant_id="tenant-a", site_id="site-1", epoch=1):
    return WorkerNode(worker_id=worker_id, site_id=site_id, tenant_id=tenant_id, runtime_version=version, state=state, fencing_epoch=epoch)


def _desired(**overrides):
    base = dict(revision_id="rev-1", target_runtime_version="2.0.0", target_worker_pool_size=2, approved_by="alice@example.com")
    base.update(overrides)
    return FleetDesiredState(**base)


# ----------------------------------------------------------------------
# Forbidden GitOps state -- structural and defense-in-depth
# ----------------------------------------------------------------------

def test_desired_state_has_no_field_for_forbidden_runtime_state():
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(FleetDesiredState)}
    forbidden = {"checkpoint", "cdc_position", "validation_state", "approval_truth", "secret",
                 "private_key", "cloud_token", "lease", "fencing_authority", "ownership_state"}
    assert field_names.isdisjoint(forbidden)


def test_config_scan_rejects_secret_shaped_key():
    with pytest.raises(GitOpsValidationError):
        _desired(config={"db_password": "hunter2"})


def test_config_scan_rejects_secret_shaped_value():
    with pytest.raises(GitOpsValidationError):
        _desired(config={"note": "token=abc123"})


def test_config_scan_rejects_ownership_or_fencing_shaped_key():
    with pytest.raises(GitOpsValidationError):
        _desired(config={"current_fencing_generation": "5"})
    with pytest.raises(GitOpsValidationError):
        _desired(config={"active_lease_id": "own-abc"})


def test_ordinary_deployment_config_is_accepted():
    d = _desired(config={"log_level": "INFO", "max_unavailable": "1", "region_hint": "ap-south-1"})
    assert d.config["log_level"] == "INFO"


def test_revision_requires_attribution():
    with pytest.raises(GitOpsValidationError):
        _desired(approved_by="")


def test_revision_requires_non_empty_id():
    with pytest.raises(GitOpsValidationError):
        _desired(revision_id="")


def test_negative_pool_size_rejected():
    with pytest.raises(GitOpsValidationError):
        _desired(target_worker_pool_size=-1)


# ----------------------------------------------------------------------
# Reconciliation truthfulness
# ----------------------------------------------------------------------

def test_in_sync_when_all_active_workers_at_target_version_and_count_matches():
    desired = _desired(target_worker_pool_size=2)
    workers = [_worker("w1", "2.0.0"), _worker("w2", "2.0.0")]
    report = reconcile_fleet_state(desired, workers)
    assert report.state == ReconciliationState.IN_SYNC


def test_pending_when_no_active_workers_yet():
    desired = _desired(target_worker_pool_size=2)
    report = reconcile_fleet_state(desired, [])
    assert report.state == ReconciliationState.PENDING


def test_partially_applied_during_mixed_version_rollout():
    desired = _desired(target_worker_pool_size=2)
    workers = [_worker("w1", "2.0.0"), _worker("w2", "1.0.0")]
    report = reconcile_fleet_state(desired, workers)
    assert report.state == ReconciliationState.PARTIALLY_APPLIED


def test_drifted_when_zero_workers_at_target_version():
    desired = _desired(target_runtime_version="3.0.0", target_worker_pool_size=2)
    workers = [_worker("w1", "2.0.0"), _worker("w2", "2.0.0")]
    report = reconcile_fleet_state(desired, workers)
    assert report.state == ReconciliationState.DRIFTED


def test_drifted_when_pool_size_mismatches_despite_correct_version():
    desired = _desired(target_worker_pool_size=5)
    workers = [_worker("w1", "2.0.0"), _worker("w2", "2.0.0")]
    report = reconcile_fleet_state(desired, workers)
    assert report.state == ReconciliationState.DRIFTED


def test_revoked_workers_excluded_from_active_count():
    desired = _desired(target_worker_pool_size=1)
    workers = [_worker("w1", "2.0.0"), _worker("w2", "2.0.0", state=WorkerState.REVOKED)]
    report = reconcile_fleet_state(desired, workers)
    assert report.active_worker_count == 1
    assert report.state == ReconciliationState.IN_SYNC


def test_incompatible_when_compatibility_callback_rejects_target_version():
    desired = _desired(target_runtime_version="99.0.0-untested")
    workers = [_worker("w1", "2.0.0")]
    report = reconcile_fleet_state(desired, workers, compatibility_callback=lambda v: v != "99.0.0-untested")
    assert report.state == ReconciliationState.INCOMPATIBLE


def test_reconciliation_never_mutates_worker_registry():
    """reconcile_fleet_state must be pure -- it never applies anything itself."""
    from akaalEngine.fabric.worker_fabric.registry import WorkerRegistry
    registry = WorkerRegistry()
    registry.register(_worker("w1", "1.0.0"))
    desired = _desired(target_runtime_version="2.0.0", target_worker_pool_size=1)
    reconcile_fleet_state(desired, list(registry.list_workers_for_tenant("tenant-a")))
    # Worker registry state completely unchanged by mere reconciliation reporting.
    assert registry.get("w1", "tenant-a").runtime_version == "1.0.0"
