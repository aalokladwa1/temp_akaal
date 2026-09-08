"""tests/security/test_p7c16_optimization_production_path.py
==================================================================
P7C.16 production-path proof: reachable through the real
PipelineUnifiedCaller/intelligence.submit seam. Owner-review Blocker 1
closure: region-scoped requests now go through the SAME real per-actor
canonical authorization P7C.8 uses (akaalPipeline.security.
CentralAuthorizationEngine via RBAC+ABAC) -- never a second authority, never
merely fail-closed-by-default. An actor with a real canonical region grant
gets that region evaluated; an actor without one does not, and the request
still succeeds (OK) with that region simply excluded and a counterfactual
explaining why -- the request as a whole is not error'd out for one illegal
region among several, matching P7C.8's own "never a union, only ever a
narrowing" discipline.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command


def _region_scoped_caller(db_path: str, tenant_id: str, principal_id: str, allowed_region: str):
    """Real RBAC (broad grant) + real ABAC DENY-unless-allowed-region policy
    -- the SAME construction akaalPipeline's own P7C.8 production-path hostile
    tests use (tests/security/test_p7c_campaign_b_production_path.py), reused
    verbatim here rather than inventing a second authorization test rig."""
    from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
    from akaalPipeline.identity.groups import GroupAuthority
    from akaalPipeline.security.abac import ABACAuthority
    from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
    from akaalPipeline.security.permission_registry import PermissionRegistry
    from akaalPipeline.security.rbac import RBACAuthority
    from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

    uow = SQLiteUnitOfWork(db_path=db_path)
    uow.initialize_schema()

    uow.tenants.create_tenant(tenant_id, tenant_id)
    uow.principals.create(tenant_id=tenant_id, principal_id=principal_id, principal_type="HUMAN", username=principal_id)

    uow.roles.create_role(role_id="baseline-role", tenant_id=tenant_id, name="Baseline")
    for perm in PermissionRegistry.ALL_PERMISSIONS:
        uow.role_permissions.assign_permission(tenant_id, "baseline-role", perm, principal_id)
    uow.role_grants.grant_role(f"grant-baseline-{principal_id}", tenant_id, "PRINCIPAL", principal_id, "baseline-role", "SYSTEM", "root", principal_id)

    uow.abac_policies.create_policy(
        tenant_id=tenant_id,
        policy_id=f"region-restriction-{tenant_id}",
        name="Canonical region restriction",
        effect="DENY",
        target_action=PermissionRegistry.INTELLIGENCE_STRATEGY_REGION_USE,
        target_resource_type="region",
        condition_expression={"not": {"in": ["resource.id", [allowed_region]]}},
        priority=10,
    )
    uow.connection.commit()

    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    real_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)

    from tests.pipeline.conftest import build_session_manager

    return PipelineUnifiedCaller(shared_uow=uow, central_authz=real_engine, session_manager=build_session_manager(uow))


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def caller(temp_db_path):
    uc = authorized_caller(db_path=temp_db_path)
    yield uc
    uc.close()


def _actor(org_id: str, actor_id: str = None) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=actor_id or f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id, workspace_id="ws-main", project_id="proj-1",
    )


def _optimize_payload(**extra_params):
    return {
        "task": "OPTIMIZE", "subject_type": "migration_plan", "subject_id": "plan-1", "subject_version": "v1",
        "capability": "performance_optimization",
        "parameters": {
            "dataset_size_bytes": 1_000_000_000, "worker_throughput_bytes_per_sec": 1_000_000,
            "validation_throughput_bytes_per_sec": 2_000_000, "cutover_window_seconds": 10_000,
            **extra_params,
        },
    }


class TestReachableThroughRealSeam:
    def test_scenario_sweep_via_real_seam(self, caller):
        actor = _actor("tenant-alpha")
        payload = _optimize_payload(candidate_worker_counts=[2, 8])
        result = caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.OK
        assert len(result.result["result"]["optimization"]["alternatives"]) == 2

    def test_region_scoped_request_via_real_central_authz(self, caller):
        """`authorized_caller`'s auto-provisioning engine grants this test
        actor a broad (SYSTEM-scoped) permission set -- so "india" comes back
        legal here. The genuinely RESTRICTIVE case (an actor with a real,
        narrow ABAC region grant that excludes a candidate) is proven by
        TestRealPerActorRegionAuthorizationThroughRealSeam below, which uses
        the same strict RBAC+ABAC construction as P7C.8's own hostile suite.
        This test only proves reachability: the resolver is real central_authz,
        not a stub that always denies or always allows regardless of the
        engine's actual decision."""
        actor = _actor("tenant-alpha")
        payload = _optimize_payload(candidate_regions=["india"])
        result = caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.OK
        assert result.result["result"]["data"]["legal_regions"] == ["india"]


class TestRealPerActorRegionAuthorizationThroughRealSeam:
    """Owner-review Blocker 1 closure: real RBAC+ABAC, the SAME engine and
    construction pattern P7C.8's own hostile suite uses, drives P7C.16's
    region legality -- never a second authority."""

    def test_granted_region_is_evaluated_ungranted_region_is_not(self, temp_db_path):
        caller = _region_scoped_caller(temp_db_path, tenant_id="tenant-rbac16", principal_id="actor-rbac16", allowed_region="india")
        try:
            actor = _actor("tenant-rbac16", actor_id="actor-rbac16")
            payload = _optimize_payload(candidate_regions=["india", "singapore"])
            result = caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["legal_regions"] == ["india"]
        finally:
            caller.close()

    def test_zero_region_grants_yields_empty_feasible_set_not_error(self, temp_db_path):
        caller = _region_scoped_caller(temp_db_path, tenant_id="tenant-rbac16b", principal_id="actor-rbac16b", allowed_region="germany")
        try:
            actor = _actor("tenant-rbac16b", actor_id="actor-rbac16b")
            payload = _optimize_payload(candidate_regions=["singapore"])
            result = caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["legal_regions"] == []
        finally:
            caller.close()

    def test_wrong_tenant_actor_cannot_borrow_another_tenants_region_grant(self, temp_db_path):
        """A caller from a DIFFERENT tenant than the one with the ABAC region
        grant cannot inherit it -- proves the authorization check is
        genuinely tenant+actor scoped, not merely region-string matching."""
        caller = _region_scoped_caller(temp_db_path, tenant_id="tenant-rbac16c", principal_id="actor-rbac16c", allowed_region="india")
        try:
            forged_actor = _actor("tenant-other-unregistered", actor_id="actor-rbac16c")
            payload = _optimize_payload(candidate_regions=["india"])
            result = caller.handle_command(make_command("intelligence.submit", payload, forged_actor, CorrelationContext.new()))
            # Either the actor/tenant is rejected outright, or the region
            # comes back excluded -- never a fabricated "india" grant for an
            # actor/tenant pairing that was never provisioned.
            if result.status == CallerResultStatus.OK:
                assert result.result["result"]["data"]["legal_regions"] == []
        finally:
            caller.close()
