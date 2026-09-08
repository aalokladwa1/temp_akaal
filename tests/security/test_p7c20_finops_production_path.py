"""tests/security/test_p7c20_finops_production_path.py
=============================================================
P7C.20 production-path proof: real PipelineUnifiedCaller -> intelligence.
submit (task=FORECAST, capability=finops_projection) -> real canonical ETA
combined with a caller-supplied organization rate.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command


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


def _submit_finops(caller, actor, migration_id, **params):
    payload = {
        "task": "FORECAST", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "finops_projection",
        "parameters": {"migration_id": migration_id, **params},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestRealCostFromCanonicalETA:
    def test_cost_computed_from_real_progress_and_supplied_rate(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=True)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            binding = caller.binding_registry.get("gateway_engine_binding")
            coord = binding.port_instance.gateway.coordinator
            coord.telemetry_authority.initialize_migration_progress("mig-1", rows_total=1_000_000)
            coord.telemetry_authority.update_progress("mig-1", add_rows=100_000)

            result = _submit_finops(caller, actor, "mig-1", worker_count=4, cost_per_worker_hour=2.0)
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["cost_status"] == "COST_PROJECTION_AVAILABLE"
        finally:
            caller.close()

    def test_no_rate_supplied_is_unknown(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            result = _submit_finops(caller, actor, "mig-1")
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["cost_status"] == "UNKNOWN"
        finally:
            caller.close()
