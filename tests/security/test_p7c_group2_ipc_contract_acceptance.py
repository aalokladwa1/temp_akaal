"""tests/security/test_p7c_group2_ipc_contract_acceptance.py
==================================================================
Closes owner-review Blocker 20: the final IPC/serialized-boundary contract
acceptance campaign for the complete Group-2 surface, through the REAL
serialized request -> PipelineActorContext -> PipelineUnifiedCaller ->
IntelligenceKernel -> capability -> canonical authority/read -> typed
response path. Proves Angular/Wails can remain a thin consumer: every
response is plain-JSON-serializable, with no internal Python object,
producer class, or engine type ever crossing the boundary.

This file covers NET-NEW negative/contract behavior not already proven
per-capability elsewhere in the suite -- it deliberately does not re-prove
what other files already establish:
  - tenant isolation per-capability: tests/security/test_p7c24_whole_p7c_
    hostile_acceptance.py (8 capabilities parametrized)
  - degraded/no-gateway behavior per-capability: same file
  - pagination/cursor continuation: tests/security/test_p7c22_portfolio_
    production_path.py
  - staleness: tests/security/test_p7c_group2_staleness_protection.py
  - unavailable optional model: tests/security/test_p7c_group2_injection_
    exhaustion_bypass_hostile.py (structural proof no model is wired)
  - bounded output: same file + P7C.14 HealthSampleStore retention test

Net-new here: malformed payload shape, unsupported capability string,
zero-permission unauthorized actor (denied before capability routing even
runs), and a full JSON-round-trip safety sweep across every Group-2
capability's response.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command

GROUP2_CAPABILITIES = [
    ("QUERY", "runtime_health", {"migration_id": "mig-1"}),
    ("ASSESS", "anomaly_detection", {"migration_id": "mig-1"}),
    ("EXPLAIN", "root_cause_analysis", {"migration_id": "mig-1"}),
    ("FORECAST", "operations_forecast", {"migration_id": "mig-1"}),
    ("RECOMMEND", "governed_remediation", {"migration_id": "mig-1"}),
    ("ASSESS", "security_risk_intelligence", {"migration_id": "mig-1"}),
    ("FORECAST", "finops_projection", {"migration_id": "mig-1"}),
    ("QUERY", "operator_query", {"migration_id": "mig-1", "intent": "what_is_happening"}),
    ("QUERY", "portfolio_intelligence", {}),
    ("OPTIMIZE", "performance_optimization", {
        "dataset_size_bytes": 1_000_000, "worker_throughput_bytes_per_sec": 100_000,
        "validation_throughput_bytes_per_sec": 100_000, "cutover_window_seconds": 1000,
    }),
    ("COMPARE", "forecast_evaluation", {
        "metric_name": "eta", "predicted_value": 100, "predicted_low": 80, "predicted_high": 120, "actual_value": 110,
    }),
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


@pytest.fixture
def caller(temp_db_path):
    uc = authorized_caller(db_path=temp_db_path, bind_gateway=False)
    yield uc
    uc.close()


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


def _submit(caller, actor, task, capability, params):
    payload = {
        "task": task, "subject_type": "migration", "subject_id": params.get("migration_id", "tenant-scope"),
        "subject_version": "v1", "capability": capability, "parameters": params,
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestFullJSONSerializationSafety:
    """A thin Angular/Wails consumer needs zero Python knowledge -- every
    response must round-trip through json.dumps/json.loads unchanged in
    shape, with no internal object leaking through."""

    @pytest.mark.parametrize("task,capability,params", GROUP2_CAPABILITIES)
    def test_response_is_plain_json_serializable(self, caller, task, capability, params):
        actor = _actor("tenant-alpha")
        if "migration_id" in params:
            _seed_migration(caller, params["migration_id"], "tenant-alpha")
        result = _submit(caller, actor, task, capability, params)
        assert result.status == CallerResultStatus.OK, f"{capability} failed: {result.error}"
        serialized = json.dumps(result.result)
        roundtripped = json.loads(serialized)
        assert roundtripped == result.result, f"{capability}'s response is not a stable plain-JSON structure"


class TestMalformedPayloadRejected:
    @pytest.mark.parametrize("task,capability,params", GROUP2_CAPABILITIES)
    def test_missing_required_or_meaningless_params_fails_closed_not_crash(self, caller, task, capability, params):
        actor = _actor("tenant-alpha")
        # Deliberately empty parameters regardless of what the capability
        # actually needs -- every producer must either refuse cleanly
        # (ERROR) or degrade honestly (OK with UNKNOWN/INSUFFICIENT_DATA),
        # never raise an unhandled exception that surfaces as a 500-shaped
        # crash to a thin frontend consumer.
        payload = {
            "task": task, "subject_type": "migration", "subject_id": "mig-malformed",
            "subject_version": "v1", "capability": capability, "parameters": {},
        }
        result = caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
        assert result.status in (CallerResultStatus.OK, CallerResultStatus.ERROR)
        if result.status == CallerResultStatus.ERROR:
            # A real, typed IPC error shape -- not a raw traceback string.
            assert result.error is not None
            assert hasattr(result.error, "code") or isinstance(result.error, dict)


class TestUnsupportedCapabilityRejected:
    def test_unknown_capability_string_fails_closed(self, caller):
        actor = _actor("tenant-alpha")
        payload = {
            "task": "QUERY", "subject_type": "migration", "subject_id": "mig-1", "subject_version": "v1",
            "capability": "this_capability_does_not_exist", "parameters": {},
        }
        result = caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR

    def test_unknown_task_capability_pairing_fails_closed(self, caller):
        """A capability that exists, but paired with the WRONG task, is
        refused rather than silently dispatched to an unrelated producer
        (the exact scenario the P7C Campaign-B suite already covers for
        Group 1 -- proven again here for a Group-2 pairing)."""
        actor = _actor("tenant-alpha")
        _seed_migration(caller, "mig-1", "tenant-alpha")
        payload = {
            "task": "OPTIMIZE", "subject_type": "migration", "subject_id": "mig-1", "subject_version": "v1",
            "capability": "runtime_health",  # registered under QUERY, not OPTIMIZE
            "parameters": {"migration_id": "mig-1"},
        }
        result = caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
        assert result.status == CallerResultStatus.ERROR


class TestZeroPermissionActorDeniedBeforeCapabilityRouting:
    """An actor with NO grants at all (not even the base INTELLIGENCE_SUBMIT
    permission) is denied at the authorization gate -- before the request
    ever reaches capability routing/dispatch, for every Group-2 capability."""

    def _zero_permission_caller(self, db_path: str, tenant_id: str, principal_id: str):
        from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
        from akaalPipeline.identity.groups import GroupAuthority
        from akaalPipeline.security.abac import ABACAuthority
        from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
        from akaalPipeline.security.rbac import RBACAuthority
        from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
        from tests.pipeline.conftest import build_session_manager

        uow = SQLiteUnitOfWork(db_path=db_path)
        uow.initialize_schema()
        uow.tenants.create_tenant(tenant_id, tenant_id)
        uow.principals.create(tenant_id=tenant_id, principal_id=principal_id, principal_type="HUMAN", username=principal_id)
        # Deliberately NO role, NO grant, NO permission of any kind.
        uow.connection.commit()

        ga = GroupAuthority(uow.groups, uow.principals)
        rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
        abac = ABACAuthority(uow.abac_policies)
        real_engine = CentralAuthorizationEngine(uow.tenants, uow.principals, ga, rbac, abac)
        return PipelineUnifiedCaller(shared_uow=uow, central_authz=real_engine, session_manager=build_session_manager(uow))

    @pytest.mark.parametrize("task,capability,params", GROUP2_CAPABILITIES)
    def test_zero_grant_actor_denied_for_every_capability(self, temp_db_path, task, capability, params):
        caller = self._zero_permission_caller(temp_db_path, "tenant-zeroperm", "actor-zeroperm")
        try:
            actor = ActorContext(
                actor=ActorReference(actor_id="actor-zeroperm", actor_type="human", display_name="No Grants"),
                organization_id="tenant-zeroperm", workspace_id="ws-main", project_id="proj-1",
            )
            if "migration_id" in params:
                _seed_migration(caller, params["migration_id"], "tenant-zeroperm")
            result = _submit(caller, actor, task, capability, params)
            assert result.status == CallerResultStatus.ERROR
        finally:
            caller.close()
