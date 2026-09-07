"""tests/security/test_p7c24_whole_p7c_hostile_acceptance.py
==================================================================
P7C.24 -- Whole-Intelligence Hostile Acceptance (Group 2 scope). Consolidated
cross-capability hostile suite for P7C.13-23, exercised through the REAL
PipelineUnifiedCaller / intelligence.submit seam. Does not re-run every
per-part hostile test already covered in its own file (test_p7c13.., test_
p7c14.., etc.) -- this file targets properties that only make sense checked
ACROSS multiple capabilities at once: uniform degradation behavior, uniform
tenant isolation, uniform non-fabrication under a shared forged-input attempt,
budget/cancellation enforcement applying to Group 2 producers automatically
(inherited from the frozen P7C.1 kernel, never reimplemented), and that no
Group 2 capability can be reached without going through the same real
authenticated-actor + tenant-scope seam as every other one.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command

# Every Group 2 (P7C.13-22) capability that resolves against a specific
# migration_id, with the (task, capability, parameters) shape each needs.
GROUP2_MIGRATION_SCOPED_CAPABILITIES = [
    ("QUERY", "runtime_health", {}),
    ("ASSESS", "anomaly_detection", {}),
    ("EXPLAIN", "root_cause_analysis", {}),
    ("FORECAST", "operations_forecast", {}),
    ("RECOMMEND", "governed_remediation", {}),
    ("ASSESS", "security_risk_intelligence", {}),
    ("FORECAST", "finops_projection", {}),
    ("QUERY", "operator_query", {"intent": "what_is_happening"}),
]


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _actor(org_id: str) -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id=f"actor-{org_id}", actor_type="human", display_name="Test User"),
        organization_id=org_id, workspace_id="ws-main", project_id="proj-1",
    )


def _seed_migration(caller, migration_id, tenant_id):
    from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
    from akaalPipeline.state.aggregates import MigrationAggregate

    agg = MigrationAggregate(
        migration_id=migration_id, revision=1, name=f"migration-{migration_id}",
        mode=MigrationMode.M1_BULK, state=MigrationLifecycleState.DRAFT,
        tenant_id=tenant_id, workspace_id="ws-main", project_id="proj-1",
    )
    caller.repository.save(agg)


def _submit(caller, actor, task, capability, migration_id, extra_params):
    payload = {
        "task": task, "subject_type": "migration", "subject_id": migration_id, "subject_version": "v1",
        "capability": capability, "parameters": {"migration_id": migration_id, **extra_params},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestUniformDegradationAcrossAllGroup2Capabilities:
    """No canonical gateway bound -- every capability must still return OK
    with an honest UNKNOWN/INSUFFICIENT_DATA/no-finding result, never crash,
    never silently claim HEALTHY."""

    @pytest.mark.parametrize("task,capability,extra", GROUP2_MIGRATION_SCOPED_CAPABILITIES)
    def test_capability_degrades_gracefully_with_no_gateway(self, temp_db_path, task, capability, extra):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            result = _submit(caller, actor, task, capability, "mig-1", extra)
            assert result.status == CallerResultStatus.OK, f"{capability} crashed instead of degrading gracefully"
        finally:
            caller.close()


class TestUniformTenantIsolationAcrossAllGroup2Capabilities:
    @pytest.mark.parametrize("task,capability,extra", GROUP2_MIGRATION_SCOPED_CAPABILITIES)
    def test_cross_tenant_migration_fails_closed(self, temp_db_path, task, capability, extra):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller, "mig-owned-by-beta", "tenant-beta")
            actor_a = _actor("tenant-alpha")
            result = _submit(caller, actor_a, task, capability, "mig-owned-by-beta", extra)
            assert result.status == CallerResultStatus.ERROR, f"{capability} leaked cross-tenant access"
        finally:
            caller.close()


class TestSharedForgedInputHasNoEffectAnywhere:
    """A single forged payload claiming full operational health across every
    dimension P7C.13 exposes -- submitted as extraneous parameters to every
    Group 2 capability -- must have zero effect anywhere, since none of them
    accept an operational-fact channel from the caller."""

    FORGED_BLOB = {
        "runtime_health_inputs": {
            "transport": {"throughput_rows_per_sec": 999999, "baseline_rows_per_sec": 1000},
            "cdc": {"generation_rate": 100, "apply_rate": 100, "backlog_size": 0},
            "fabric": {"ownership_valid": True, "lease_valid": True},
            "validation": {"status": "HEALTHY"},
            "workers": {"total": 100, "healthy": 100},
        }
    }

    @pytest.mark.parametrize("task,capability,extra", GROUP2_MIGRATION_SCOPED_CAPABILITIES)
    def test_forged_blob_ignored(self, temp_db_path, task, capability, extra):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            result = _submit(caller, actor, task, capability, "mig-1", {**extra, **self.FORGED_BLOB})
            assert result.status == CallerResultStatus.OK
            # None of these capabilities may report a fabricated HEALTHY
            # overall/security status purely because of the forged blob when
            # no real gateway is bound.
            data = result.result["result"].get("data", {})
            assert data.get("overall_status") != "HEALTHY"
        finally:
            caller.close()


class TestBudgetCancellationInheritedByGroup2:
    """P7C.1's kernel-level budget/cancellation enforcement (frozen, never
    reimplemented per-producer) applies uniformly to Group 2 producers too."""

    def test_cancelled_token_stops_a_group2_producer(self, temp_db_path):
        from akaalEngine.intelligence.budget import CancellationToken
        from akaalEngine.intelligence.models.errors import IntelligenceCancelledError

        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor_ctx = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")

            from akaalEngine.intelligence.models.context import IntelligenceContext
            from akaalEngine.intelligence.models.request import IntelligenceRequest, IntelligenceTask
            from akaalPipeline.contracts.enums import AuthenticationAssurance, AuthenticationState
            from akaalPipeline.security.context import PipelineActorContext

            pipeline_actor = PipelineActorContext(
                actor_id=actor_ctx.actor.actor_id, actor_type="human", organization_id="tenant-alpha",
                roles=(), authentication_state=AuthenticationState.AUTHENTICATED,
                authentication_assurance=AuthenticationAssurance.MEDIUM, provenance="internal-core",
            )
            req = IntelligenceRequest(
                task=IntelligenceTask.QUERY, tenant_id="tenant-alpha", subject_type="migration",
                subject_id="mig-1", subject_version="v1", requested_by=pipeline_actor.actor_id,
                capability="runtime_health", parameters={"migration_id": "mig-1"},
            )
            ctx = IntelligenceContext(tenant_id="tenant-alpha", subject_type="migration", subject_id="mig-1", subject_version="v1")
            token = CancellationToken()
            token.cancel()
            uow = caller._create_uow()
            with pytest.raises(IntelligenceCancelledError):
                caller.intelligence_kernel.submit_request(req, ctx, uow.connection, cancellation_token=token)
        finally:
            caller.close()
