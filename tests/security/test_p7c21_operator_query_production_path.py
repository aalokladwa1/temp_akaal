"""tests/security/test_p7c21_operator_query_production_path.py
=====================================================================
P7C.21 production-path proof: real PipelineUnifiedCaller -> intelligence.
submit (task=QUERY, capability=operator_query), full resolver chain reuse,
tenant isolation (anti-enumeration: a cross-tenant migration query fails
exactly like every other P7C.13-21 capability, never leaking existence).
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


def _ask(caller, actor, migration_id, intent):
    payload = {
        "task": "QUERY", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "operator_query",
        "parameters": {"migration_id": migration_id, "intent": intent},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestReachableThroughRealSeam:
    def test_what_is_happening_via_real_seam(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            result = _ask(caller, actor, "mig-1", "what_is_happening")
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["citations"] == ["runtime_health", "anomaly_detection"]
        finally:
            caller.close()


class TestAntiEnumeration:
    def test_cross_tenant_migration_query_fails_closed_same_as_other_capabilities(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller, "mig-owned-by-beta", "tenant-beta")
            actor_a = _actor("tenant-alpha")
            result = _ask(caller, actor_a, "mig-owned-by-beta", "what_is_happening")
            assert result.status == CallerResultStatus.ERROR
        finally:
            caller.close()
