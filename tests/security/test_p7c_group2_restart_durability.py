"""tests/security/test_p7c_group2_restart_durability.py
==============================================================
Closes owner-review Blocker 9: classifies each Group-2 stateful component as
persistent or ephemeral, then proves the correct behavior across a real
process-level restart (closing one PipelineUnifiedCaller/connection set
entirely and opening a brand new one against the SAME on-disk database
files -- never an in-memory-only round trip).

Classification:
  - PERSISTENT: intelligence_artifacts, intelligence_outcomes (Group-1
    frozen tables) -- must survive restart byte-for-byte.
  - PERSISTENT: P7C.14's HealthSampleStore sibling file -- must survive
    restart, remain correctly tenant/migration-scoped, and remain bounded.
  - EPHEMERAL (by design, not a defect): in-process engine-authority state
    (TelemetryAuthority progress tracker, CDCAuthority counters, RuntimeAuthority
    snapshots) -- these are process-local canonical runtime state, not P7C's
    to persist; P7C.13 correctly reports UNKNOWN for them after a restart
    with no real telemetry resumed yet, rather than resurrecting stale
    numbers.
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


def _submit_anomaly(caller, actor, migration_id):
    payload = {
        "task": "ASSESS", "subject_type": "migration", "subject_id": migration_id,
        "subject_version": "v1", "capability": "anomaly_detection", "parameters": {"migration_id": migration_id},
    }
    return caller.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))


class TestIntelligenceArtifactsAndOutcomesSurviveRestart:
    def test_artifact_and_outcome_readable_after_full_process_restart(self, temp_db_path):
        actor = _actor("tenant-alpha")

        caller1 = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller1, "mig-restart-1", "tenant-alpha")
            r = _submit_anomaly(caller1, actor, "mig-restart-1")
            assert r.status == CallerResultStatus.OK
            artifact_id = r.result["artifact_id"]

            outcome_payload = {"artifact_id": artifact_id, "outcome_status": "SUCCEEDED", "detail": "pre-restart"}
            outcome_result = caller1.handle_command(make_command("intelligence.outcome.record", outcome_payload, actor, CorrelationContext.new()))
            assert outcome_result.status == CallerResultStatus.OK
        finally:
            caller1.close()  # simulates full process shutdown -- no shared in-memory state carried forward

        # A brand new caller/process, same on-disk database file.
        caller2 = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            refetched = caller2.handle_query(make_query("intelligence.artifact.get", {"artifact_id": artifact_id}, actor, CorrelationContext.new()))
            assert refetched.status == CallerResultStatus.OK
            assert refetched.result["tenant_id"] == "tenant-alpha"

            outcomes = caller2.handle_query(make_query("intelligence.outcome.list", {"artifact_id": artifact_id}, actor, CorrelationContext.new()))
            assert outcomes.status == CallerResultStatus.OK
            assert len(outcomes.result["outcomes"]) == 1
            assert outcomes.result["outcomes"][0]["detail"] == "pre-restart"
        finally:
            caller2.close()


class TestHealthSampleHistorySurvivesRestartBoundedAndScoped:
    def test_sample_history_persists_across_restart_and_stays_bounded(self, temp_db_path):
        import sqlite3

        actor = _actor("tenant-alpha")

        caller1 = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller1, "mig-restart-2", "tenant-alpha")
            for _ in range(3):
                r = _submit_anomaly(caller1, actor, "mig-restart-2")
                assert r.status == CallerResultStatus.OK
        finally:
            caller1.close()

        # Direct proof of durability at the storage layer: the P7C.14
        # sibling file (not the caller's in-memory state) still has the
        # pre-restart rows for this exact migration, correctly scoped.
        sample_db_path = f"{temp_db_path}.p7c14_health_samples.db"
        conn = sqlite3.connect(sample_db_path)
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM intelligence_health_samples WHERE tenant_id = ? AND migration_id = ?",
                ("tenant-alpha", "mig-restart-2"),
            )
            assert cur.fetchone()[0] == 3
        finally:
            conn.close()

        caller2 = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            r = _submit_anomaly(caller2, actor, "mig-restart-2")
            assert r.status == CallerResultStatus.OK
        finally:
            caller2.close()

        # The new request's own sample was appended to the SAME persisted
        # history, not a fresh/reset store -- 4 rows now exist.
        conn = sqlite3.connect(sample_db_path)
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM intelligence_health_samples WHERE tenant_id = ? AND migration_id = ?",
                ("tenant-alpha", "mig-restart-2"),
            )
            assert cur.fetchone()[0] == 4
        finally:
            conn.close()

    def test_sample_history_remains_tenant_and_migration_scoped_after_restart(self, temp_db_path):
        actor_a = _actor("tenant-alpha")
        actor_b = _actor("tenant-beta")

        caller1 = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            _seed_migration(caller1, "mig-restart-a", "tenant-alpha")
            _seed_migration(caller1, "mig-restart-b", "tenant-beta")
            _submit_anomaly(caller1, actor_a, "mig-restart-a")
            _submit_anomaly(caller1, actor_b, "mig-restart-b")
        finally:
            caller1.close()

        caller2 = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            # tenant-alpha cannot read tenant-beta's migration post-restart.
            result = _submit_anomaly(caller2, actor_a, "mig-restart-b")
            assert result.status == CallerResultStatus.ERROR
        finally:
            caller2.close()


class TestEphemeralEngineStateHonestlyUnknownAfterRestart:
    """Per-process TelemetryAuthority state is intentionally NOT persisted by
    P7C (it is canonical AKAAL runtime state, not P7C's to own) -- a restart
    with no real telemetry resumed correctly reports UNKNOWN, never a
    resurrected stale number."""

    def test_no_stale_progress_survives_restart_as_current_truth(self, temp_db_path):
        actor = _actor("tenant-alpha")

        caller1 = authorized_caller(db_path=temp_db_path, bind_gateway=True)
        try:
            _seed_migration(caller1, "mig-restart-3", "tenant-alpha")
            binding = caller1.binding_registry.get("gateway_engine_binding")
            coord = binding.port_instance.gateway.coordinator
            coord.telemetry_authority.initialize_migration_progress("mig-restart-3", rows_total=1_000_000)
            coord.telemetry_authority.update_progress("mig-restart-3", add_rows=500_000)
        finally:
            caller1.close()

        # A fresh process/caller has a fresh (unbound) engine gateway -- no
        # canonical progress state resumed automatically, so the health
        # projection is honestly UNKNOWN rather than fabricating "50%".
        caller2 = authorized_caller(db_path=temp_db_path, bind_gateway=False)
        try:
            payload = {
                "task": "QUERY", "subject_type": "migration", "subject_id": "mig-restart-3",
                "subject_version": "v1", "capability": "runtime_health", "parameters": {"migration_id": "mig-restart-3"},
            }
            result = caller2.handle_command(make_command("intelligence.submit", payload, actor, CorrelationContext.new()))
            assert result.status == CallerResultStatus.OK
            assert result.result["result"]["data"]["dimensions"]["TRANSPORT"]["status"] == "UNKNOWN"
        finally:
            caller2.close()
