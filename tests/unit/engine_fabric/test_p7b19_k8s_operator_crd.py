"""
P7B.19 -- AKAAL Kubernetes Operator & CRDs: reconciliation positive + hostile tests.
"""

import inspect

import pytest

from akaalEngine.fabric.k8s_runtime.crd import (
    AkaalWorkerPoolSpec,
    CRDValidationError,
    reconcile_worker_pool,
)
from akaalEngine.fabric.k8s_runtime.pod_spec import ResourceRequirements
from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState


def _resources():
    return ResourceRequirements(cpu_request="500m", memory_request="512Mi", cpu_limit="1", memory_limit="1Gi")


def _spec(replicas=3, pool="pool-1", site="site-1", tenant="t1"):
    return AkaalWorkerPoolSpec(pool_id=pool, site_id=site, tenant_id=tenant, desired_replicas=replicas,
                                image="akaal/worker:1.0.0", runtime_version="1.0.0", resources=_resources())


def _worker(worker_id, site="site-1", tenant="t1", state=WorkerState.IDLE, epoch=1):
    return WorkerNode(worker_id=worker_id, site_id=site, tenant_id=tenant, runtime_version="1.0.0",
                       state=state, fencing_epoch=epoch)


# ------------------------------------------------------------------ CRD ownership boundary (structural)


def test_crd_spec_has_no_field_for_migration_or_plan_truth():
    field_names = set(inspect.signature(AkaalWorkerPoolSpec).parameters.keys())
    forbidden = {"migration_id", "execution_plan", "plan_fingerprint", "checkpoint",
                 "cdc_offset", "validation_result", "approval", "secret", "credential", "password"}
    assert field_names.isdisjoint(forbidden)


def test_crd_spec_has_no_field_capable_of_holding_a_literal_secret():
    field_names = set(inspect.signature(AkaalWorkerPoolSpec).parameters.keys())
    for name in field_names:
        assert "secret" not in name.lower()
        assert "password" not in name.lower()
        assert "credential" not in name.lower()


def test_assignment_reference_is_opaque_string_not_a_plan_object():
    spec = AkaalWorkerPoolSpec(pool_id="p", site_id="s", tenant_id="t", desired_replicas=1,
                                image="img:1", runtime_version="1.0.0", resources=_resources(),
                                assignment_reference="fingerprint-abc123")
    assert isinstance(spec.assignment_reference, str)


# ------------------------------------------------------------------ positive reconciliation


def test_matching_replica_count_is_noop():
    desired = _spec(replicas=2)
    observed = [_worker("w1"), _worker("w2")]
    plan = reconcile_worker_pool(desired, observed)
    assert plan.is_noop()


def test_under_provisioned_recommends_scale_out():
    desired = _spec(replicas=5)
    observed = [_worker("w1"), _worker("w2")]
    plan = reconcile_worker_pool(desired, observed)
    assert plan.actions[0].kind == "SCALE_OUT"
    assert "deficit of 3" in plan.actions[0].reason


def test_over_provisioned_recommends_scale_in_deterministic_selection():
    desired = _spec(replicas=1)
    observed = [_worker("w1", epoch=3), _worker("w2", epoch=1), _worker("w3", epoch=2)]
    plan = reconcile_worker_pool(desired, observed)
    assert plan.actions[0].kind == "SCALE_IN"
    # surplus of 2 (3 observed - 1 desired): lowest fencing_epoch drained first --
    # w2 (epoch=1) then w3 (epoch=2); w1 (epoch=3, newest) is kept.
    assert plan.actions[0].worker_ids == ("w2", "w3")


# ------------------------------------------------------------------ hostile


def test_revoked_workers_never_count_toward_satisfied_desired_state():
    desired = _spec(replicas=2)
    observed = [_worker("w1", state=WorkerState.REVOKED), _worker("w2", state=WorkerState.REVOKED)]
    plan = reconcile_worker_pool(desired, observed)
    assert plan.actions[0].kind == "SCALE_OUT"  # revoked workers don't satisfy desired count


def test_stale_workers_never_count_toward_satisfied_desired_state():
    desired = _spec(replicas=1)
    observed = [_worker("w1", state=WorkerState.STALE)]
    plan = reconcile_worker_pool(desired, observed)
    assert plan.actions[0].kind == "SCALE_OUT"


def test_workers_from_other_site_or_tenant_never_counted():
    desired = _spec(replicas=1, site="site-1", tenant="t1")
    observed = [_worker("w1", site="site-2", tenant="t1"), _worker("w2", site="site-1", tenant="t2-attacker")]
    plan = reconcile_worker_pool(desired, observed)
    assert plan.actions[0].kind == "SCALE_OUT"  # neither observed worker is in-scope


def test_duplicate_reconciliation_calls_are_idempotent():
    desired = _spec(replicas=3)
    observed = [_worker("w1"), _worker("w2")]
    plan1 = reconcile_worker_pool(desired, observed)
    plan2 = reconcile_worker_pool(desired, observed)
    assert plan1 == plan2  # calling twice never produces a different/duplicated decision


def test_negative_desired_replicas_rejected():
    with pytest.raises(CRDValidationError):
        AkaalWorkerPoolSpec(pool_id="p", site_id="s", tenant_id="t", desired_replicas=-1,
                             image="img:1", runtime_version="1.0.0", resources=_resources())


def test_empty_pool_id_rejected():
    with pytest.raises(CRDValidationError):
        AkaalWorkerPoolSpec(pool_id="", site_id="s", tenant_id="t", desired_replicas=1,
                             image="img:1", runtime_version="1.0.0", resources=_resources())


def test_zero_desired_replicas_with_active_workers_recommends_full_scale_in():
    desired = _spec(replicas=0)
    observed = [_worker("w1"), _worker("w2")]
    plan = reconcile_worker_pool(desired, observed)
    assert plan.actions[0].kind == "SCALE_IN"
    assert set(plan.actions[0].worker_ids) == {"w1", "w2"}


def test_empty_observed_and_zero_desired_is_noop():
    plan = reconcile_worker_pool(_spec(replicas=0), [])
    assert plan.is_noop()
