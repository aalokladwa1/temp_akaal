"""tests/security/test_p7c23_forecast_provenance_chain.py
================================================================
Closes owner-review Blocker 14: proves the forecast -> actual -> evaluation
identity/provenance chain survives across real, repeated requests. Every
IntelligenceArtifact already carries artifact_id/algorithm_version/
policy_version/canonical_state_fingerprint/created_at (frozen P7C.1 kernel
contract) and IntelligenceArtifactStore.save is INSERT-only -- this test
proves that structural guarantee actually holds for P7C.17 forecasts
specifically, and that P7C.23's evaluator preserves the link.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from tests.pipeline.conftest import authorized_caller, make_command, make_query


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


def _submit_forecast(caller, actor, migration_id):
    payload = {
        "task": "FORECAST", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "operations_forecast",
        "parameters": {"migration_id": migration_id},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestForecastImmutabilityAcrossRepeatedRequests:
    def test_two_forecast_requests_get_two_distinct_never_overwritten_artifacts(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=True)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            binding = caller.binding_registry.get("gateway_engine_binding")
            coord = binding.port_instance.gateway.coordinator
            coord.telemetry_authority.initialize_migration_progress("mig-1", rows_total=1_000_000)
            coord.telemetry_authority.update_progress("mig-1", add_rows=100_000)

            r1 = _submit_forecast(caller, actor, "mig-1")
            assert r1.status == CallerResultStatus.OK
            artifact_id_1 = r1.result["artifact_id"]
            created_at_1 = r1.result["created_at"]

            coord.telemetry_authority.update_progress("mig-1", add_rows=200_000)
            r2 = _submit_forecast(caller, actor, "mig-1")
            assert r2.status == CallerResultStatus.OK
            artifact_id_2 = r2.result["artifact_id"]

            # Two distinct artifacts -- the second forecast never overwrote the first.
            assert artifact_id_1 != artifact_id_2

            # The FIRST artifact, re-fetched after the second was created, is
            # byte-for-byte the same prediction it always was -- proving
            # IntelligenceArtifactStore never mutates `result` in place.
            refetched = caller.handle_query(make_query("intelligence.artifact.get", {"artifact_id": artifact_id_1}, actor, CorrelationContext.new()))
            assert refetched.status == CallerResultStatus.OK
            assert refetched.result["created_at"] == created_at_1
            assert refetched.result["result"]["data"] == r1.result["result"]["data"]
        finally:
            caller.close()


class TestEvaluationPreservesForecastLinkage:
    def test_evaluation_carries_forecast_artifact_id_through(self, temp_db_path):
        caller = authorized_caller(db_path=temp_db_path, bind_gateway=True)
        try:
            actor = _actor("tenant-alpha")
            _seed_migration(caller, "mig-1", "tenant-alpha")
            binding = caller.binding_registry.get("gateway_engine_binding")
            coord = binding.port_instance.gateway.coordinator
            coord.telemetry_authority.initialize_migration_progress("mig-1", rows_total=1_000_000)
            coord.telemetry_authority.update_progress("mig-1", add_rows=500_000)

            forecast_result = _submit_forecast(caller, actor, "mig-1")
            assert forecast_result.status == CallerResultStatus.OK
            forecast_artifact_id = forecast_result.result["artifact_id"]
            predictions = forecast_result.result["result"]["predictions"]
            eta_pred = next((p for p in predictions if p["metric"] == "migration_eta_seconds"), None)
            assert eta_pred is not None

            eval_payload = {
                "task": "COMPARE", "subject_type": "migration", "subject_id": "mig-1", "subject_version": "v1",
                "capability": "forecast_evaluation",
                "parameters": {
                    "metric_name": "migration_eta_seconds", "predicted_value": eta_pred["value"],
                    "predicted_low": eta_pred["low"], "predicted_high": eta_pred["high"],
                    "actual_value": eta_pred["value"] * 1.1,
                    "forecast_artifact_id": forecast_artifact_id,
                },
            }
            eval_result = caller.handle_command(make_command("intelligence.submit", eval_payload, actor, CorrelationContext.new()))
            assert eval_result.status == CallerResultStatus.OK
            assert eval_result.result["result"]["data"]["forecast_artifact_id"] == forecast_artifact_id

            # The evaluation artifact itself is independently retrievable and
            # tenant-bound, exactly like any other P7C artifact.
            eval_artifact_id = eval_result.result["artifact_id"]
            refetched = caller.handle_query(make_query("intelligence.artifact.get", {"artifact_id": eval_artifact_id}, actor, CorrelationContext.new()))
            assert refetched.status == CallerResultStatus.OK
            assert refetched.result["result"]["data"]["forecast_artifact_id"] == forecast_artifact_id
        finally:
            caller.close()
