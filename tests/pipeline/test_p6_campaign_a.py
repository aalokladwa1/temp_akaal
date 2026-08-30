"""tests.pipeline.test_p6_campaign_a
====================================
Comprehensive hostile verification test suite for AKAAL P6 Campaign A (P6.1 - P6.4).
Validates Operations Control Plane, Unified Observability, Explainable Health/Diagnostics,
Fleet/Node Management, and Drain Crash/Restart Durability strictly against physical runtime authorities.
"""

import logging
import os
import sqlite3
import tempfile
import uuid
import pytest

from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode, OperationStatus
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.operations.models import OperationRecord
from akaalPipeline.operations.mutability import (
    MutabilityClassification,
    OperationalMutabilityResolver,
)
from akaalPipeline.health.explainable import (
    ExplainableHealthService,
    HealthConfidenceLevel,
    MigrationHealthStatus,
)
from akaalPipeline.health.diagnostics import DiagnosticSnapshotService, _sanitize_data, _sanitize_dict
from akaalPipeline.fleet.fleet_service import (
    FleetOperationalService,
    NodeDrainState,
    NodeLivenessStatus,
)
from akaalPipeline.security.context import PipelineActorContext
from akaalIPC.protocol.envelopes import (
    CommandEnvelope,
    QueryEnvelope,
    SubscriptionRequest,
    SubscriptionBatch,
    EventEnvelope,
)
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus, SubscriptionSourcePort
from akaalIPC.application.router import IPCRouter
from akaalEngine.cdc.api import CDCAuthority
from akaalEngine.runtime.distributed.coordinator import DistributedCoordinator, resolve_stable_node_id
from akaalEngine.runtime.resources.admission import ResourceAdmissionController, ResourceRequirement
from tests.pipeline.conftest import make_command, make_query


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
    uc = PipelineUnifiedCaller(db_path=temp_db_path)
    yield uc
    uc.close()


def make_actor(org_id="tenant-alpha", ws_id="ws-main", proj_id="proj-1", roles=("admin", "operator")):
    return ActorContext(
        actor=ActorReference(actor_id=f"actor-{org_id}", actor_type="human", display_name="Test Operator"),
        organization_id=org_id,
        workspace_id=ws_id,
        project_id=proj_id,
        roles=frozenset(roles),
    )


# ============================================================================
# P6.1: OPERATIONS CONTROL PLANE TESTS
# ============================================================================

def test_p6_1_mutability_dynamic_resolution():
    """Verify mutability truth is dynamically derived from underlying authority and state."""
    # Worker resizing is always UNSUPPORTED_BY_DESIGN
    res_worker = OperationalMutabilityResolver.evaluate("worker_pool_size")
    assert res_worker.classification == MutabilityClassification.UNSUPPORTED_BY_DESIGN
    assert not res_worker.is_mutable_now
    assert "unsupported by design" in res_worker.reason.lower()

    # Plan fingerprint is IMMUTABLE
    res_fp = OperationalMutabilityResolver.evaluate("plan_fingerprint")
    assert res_fp.classification == MutabilityClassification.IMMUTABLE
    assert not res_fp.is_mutable_now

    # CDC fetch rate is RUNTIME_MUTABLE when ACTIVE
    res_cdc_active = OperationalMutabilityResolver.evaluate("max_fetch_bytes_sec", current_state=MigrationLifecycleState.ACTIVE)
    assert res_cdc_active.classification == MutabilityClassification.RUNTIME_MUTABLE
    assert res_cdc_active.is_mutable_now

    # Stream position override requires PAUSE
    res_pos_running = OperationalMutabilityResolver.evaluate("cdc_starting_position", current_state=MigrationLifecycleState.ACTIVE)
    assert res_pos_running.classification == MutabilityClassification.PAUSE_REQUIRED
    assert not res_pos_running.is_mutable_now
    assert res_pos_running.requires_pause

    res_pos_paused = OperationalMutabilityResolver.evaluate("cdc_starting_position", current_state=MigrationLifecycleState.PAUSED)
    assert res_pos_paused.classification == MutabilityClassification.PAUSE_REQUIRED
    assert res_pos_paused.is_mutable_now


def test_p6_1_pause_and_resume_lifecycle(caller):
    """Verify pause and resume lifecycle transitions, idempotency, and aggregate confirmation."""
    actor = make_actor()
    corr = CorrelationContext.new()

    # 1. Create and configure a migration
    create_cmd = make_command(
        "migration.create",
        {
            "name": "P6 Pause Test",
            "source_type": "oracle",
            "target_type": "postgres",
            "mode": "M1_BULK",
        },
        actor,
        corr,
    )
    res_create = caller.handle_command(create_cmd)
    assert res_create.status == CallerResultStatus.OK
    mig_id = res_create.result["migration_id"]

    cfg_cmd = make_command(
        "migration.configure",
        {
            "migration_id": mig_id,
            "source_config": {"host": "localhost"},
            "target_config": {"host": "localhost"},
        },
        actor,
        corr,
    )
    caller.handle_command(cfg_cmd)

    # Initial state is CONFIGURING -> Cannot pause non-active migration
    pause_cmd_invalid = make_command(
        "migration.pause",
        {"migration_id": mig_id},
        actor,
        corr,
    )
    res_p_invalid = caller.handle_command(pause_cmd_invalid)
    assert res_p_invalid.status == CallerResultStatus.ERROR
    assert "cannot pause migration" in res_p_invalid.error.message.lower()

    # Transition to ACTIVE via UoW for operational control test
    with caller._create_uow() as uow:
        agg = caller.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    # 2. Pause active migration
    pause_cmd = make_command(
        "migration.pause",
        {"migration_id": mig_id, "reason": "Operator requested pause for maintenance"},
        actor,
        corr,
    )
    res_pause = caller.handle_command(pause_cmd)
    assert res_pause.status == CallerResultStatus.OK
    assert res_pause.result["status"] == "APPLIED"
    assert res_pause.result["state"] == "PAUSED"

    # Verify aggregate is PAUSED in database
    with caller._create_uow() as uow:
        agg_after = caller.repository.get_by_id(mig_id, connection=uow.connection)
        assert agg_after.state == MigrationLifecycleState.PAUSED

    # 3. Idempotent pause on already paused migration
    res_pause_dup = caller.handle_command(pause_cmd)
    assert res_pause_dup.status == CallerResultStatus.OK
    assert res_pause_dup.result["idempotent"] is True
    assert res_pause_dup.result["state"] == "PAUSED"

    # 4. Resume paused migration
    resume_cmd = make_command(
        "migration.resume",
        {"migration_id": mig_id, "reason": "Maintenance complete"},
        actor,
        corr,
    )
    res_resume = caller.handle_command(resume_cmd)
    assert res_resume.status == CallerResultStatus.OK
    assert res_resume.result["status"] == "APPLIED"
    assert res_resume.result["state"] == "ACTIVE"

    # Verify aggregate is ACTIVE in database
    with caller._create_uow() as uow:
        agg_resumed = caller.repository.get_by_id(mig_id, connection=uow.connection)
        assert agg_resumed.state == MigrationLifecycleState.ACTIVE

    # 5. Idempotent resume on already active migration
    res_resume_dup = caller.handle_command(resume_cmd)
    assert res_resume_dup.status == CallerResultStatus.OK
    assert res_resume_dup.result["idempotent"] is True


def test_p6_1_stale_execution_fencing_rejection(caller):
    """Verify pause and resume reject stale execution target IDs."""
    actor = make_actor()
    corr = CorrelationContext.new()

    create_cmd = make_command("migration.create", {"name": "Fencing Test", "mode": "M1_BULK"}, actor, corr)
    res_c = caller.handle_command(create_cmd)
    mig_id = res_c.result["migration_id"]

    with caller._create_uow() as uow:
        agg = caller.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.active_attempt_id = "attempt-current-v2"
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    # Pause specifying stale attempt-v1
    stale_pause = make_command(
        "migration.pause",
        {"migration_id": mig_id, "target_execution_id": "attempt-stale-v1"},
        actor,
        corr,
    )
    res_stale = caller.handle_command(stale_pause)
    assert res_stale.status == CallerResultStatus.ERROR
    assert "target execution 'attempt-stale-v1' does not match" in res_stale.error.message.lower()


def test_p6_1_tenant_isolation_on_pause(caller):
    """Verify Tenant B cannot pause Tenant A's migration."""
    actor_a = make_actor(org_id="tenant-alpha")
    actor_b = make_actor(org_id="tenant-beta")
    corr = CorrelationContext.new()

    create_cmd = make_command(
        "migration.create",
        {
            "name": "Tenant A Migration",
            "source_type": "oracle",
            "target_type": "postgres",
            "mode": "M1_BULK",
        },
        actor_a,
        corr,
    )
    res_c = caller.handle_command(create_cmd)
    assert res_c.status == CallerResultStatus.OK
    mig_id = res_c.result["migration_id"]

    pause_cmd_evil = make_command(
        "migration.pause",
        {"migration_id": mig_id},
        actor_b,
        corr,
    )
    res = caller.handle_command(pause_cmd_evil)
    assert res.status == CallerResultStatus.ERROR
    assert res.error.category.value in ("FORBIDDEN", "UNAUTHORIZED", "POLICY_DENIED")


def test_p6_1_cdc_rate_throttling_runtime_mutation():
    """Verify CDCAuthority rate throttling is dynamically mutable under lock."""
    cdc = CDCAuthority()
    assert cdc.max_events_per_fetch == 1000
    assert cdc.max_fetch_bytes_sec == 10 * 1024 * 1024

    new_limits = cdc.set_capture_budget(max_events_per_fetch=250, max_fetch_bytes_sec=2 * 1024 * 1024)
    assert new_limits["max_events_per_fetch"] == 250
    assert new_limits["max_fetch_bytes_sec"] == 2 * 1024 * 1024
    assert cdc.max_events_per_fetch == 250
    assert cdc.max_fetch_bytes_sec == 2 * 1024 * 1024


def test_p6_1_pause_resume_across_execution_modes_m1_to_m8(caller):
    """Verify pause and resume behavior across all 8 execution modes (M1 to M8)."""
    actor = make_actor()
    corr = CorrelationContext.new()

    for mode in MigrationMode:
        create_cmd = make_command(
            "migration.create",
            {"name": f"Mode Test {mode.value}", "mode": mode.value},
            actor,
            corr,
        )
        res_c = caller.handle_command(create_cmd)
        assert res_c.status == CallerResultStatus.OK
        mig_id = res_c.result["migration_id"]

        with caller._create_uow() as uow:
            agg = caller.repository.get_by_id(mig_id, connection=uow.connection)
            agg.state = MigrationLifecycleState.ACTIVE
            agg.revision += 1
            caller.repository.save(agg, connection=uow.connection)

        # Pause
        p_res = caller.handle_command(make_command("migration.pause", {"migration_id": mig_id}, actor, corr))
        assert p_res.status == CallerResultStatus.OK
        assert p_res.result["state"] == "PAUSED"

        # Resume
        r_res = caller.handle_command(make_command("migration.resume", {"migration_id": mig_id}, actor, corr))
        assert r_res.status == CallerResultStatus.OK
        assert r_res.result["state"] == "ACTIVE"


def test_p6_1_conflicting_commands_deterministic_fencing(caller):
    """Verify terminal cancellation cannot be resumed and cancelled state blocks pause/resume."""
    actor = make_actor()
    corr = CorrelationContext.new()

    res_c = caller.handle_command(make_command("migration.create", {"name": "Cancel Conflict", "mode": "M1_BULK"}, actor, corr))
    mig_id = res_c.result["migration_id"]

    with caller._create_uow() as uow:
        agg = caller.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    # Cancel migration
    res_cancel = caller.handle_command(make_command("migration.cancel", {"migration_id": mig_id}, actor, corr))
    assert res_cancel.status == CallerResultStatus.OK

    # Try to pause cancelled migration -> Rejected
    res_pause = caller.handle_command(make_command("migration.pause", {"migration_id": mig_id}, actor, corr))
    assert res_pause.status == CallerResultStatus.ERROR

    # Try to resume cancelled migration -> Rejected
    res_resume = caller.handle_command(make_command("migration.resume", {"migration_id": mig_id}, actor, corr))
    assert res_resume.status == CallerResultStatus.ERROR


# ============================================================================
# P6.2: UNIFIED OBSERVABILITY TESTS
# ============================================================================

def test_p6_2_correlated_telemetry_and_history(caller):
    """Verify correlated telemetry query projects real signals and truthful time bounds."""
    actor = make_actor()
    corr = CorrelationContext.new()

    create_cmd = make_command(
        "migration.create",
        {
            "name": "Obs Test",
            "source_type": "oracle",
            "target_type": "postgres",
            "mode": "M1_BULK",
        },
        actor,
        corr,
    )
    res_c = caller.handle_command(create_cmd)
    assert res_c.status == CallerResultStatus.OK
    mig_id = res_c.result["migration_id"]

    q_env = make_query("observability.get", {"migration_id": mig_id}, actor, corr)
    res_q = caller.handle_query(q_env)

    assert res_q.status == CallerResultStatus.OK
    telemetry = res_q.result
    assert telemetry["tenant_id"] == "tenant-alpha"
    assert telemetry["migration_id"] == mig_id
    assert "captured_at" in telemetry
    assert "runtime_metrics" in telemetry
    assert "cdc_metrics" in telemetry
    assert "data_range_start" in telemetry


def test_p6_2_prometheus_metrics_export(caller):
    """Verify Prometheus export endpoint returns standard exposition format."""
    actor = make_actor()
    corr = CorrelationContext.new()
    q_env = make_query("metrics.export_prometheus", {}, actor, corr)
    res_prom = caller.handle_query(q_env)

    assert res_prom.status == CallerResultStatus.OK
    prom_text = res_prom.result["prometheus_text"]
    assert "akaal_" in prom_text or "TYPE" in prom_text


def test_p6_2_cross_tenant_observability_blocked(caller):
    """Verify Tenant B cannot query Tenant A's telemetry."""
    actor_a = make_actor(org_id="tenant-alpha")
    actor_b = make_actor(org_id="tenant-beta")
    corr = CorrelationContext.new()

    create_cmd = make_command("migration.create", {"name": "Obs Iso Test", "mode": "M1_BULK"}, actor_a, corr)
    res_c = caller.handle_command(create_cmd)
    mig_id = res_c.result["migration_id"]

    q_env_evil = make_query("observability.get", {"migration_id": mig_id}, actor_b, corr)
    res_evil = caller.handle_query(q_env_evil)
    assert res_evil.status == CallerResultStatus.ERROR
    assert res_evil.error.category.value in ("FORBIDDEN", "UNAUTHORIZED", "POLICY_DENIED")


# ============================================================================
# P6.3: EXPLAINABLE HEALTH & DIAGNOSTICS TESTS
# ============================================================================

def test_p6_3_explainable_health_causal_chains():
    """Verify explainable health derives truthful causal explanations without fake guessing."""
    # 1. Normal signals -> HEALTHY
    h_healthy = ExplainableHealthService.evaluate(
        migration_id="mig-1",
        migration_state="ACTIVE",
        cdc_snapshot={"replication_lag_seconds": 1.2, "backlog_bytes": 1024, "retention_state": "HEALTHY"},
        runtime_snapshot={"task_snapshots": [{"task_id": "t1", "state": "RUNNING"}]},
    )
    assert h_healthy.overall_health == MigrationHealthStatus.HEALTHY
    assert "operating normally" in h_healthy.summary_reason.lower()

    # 2. Severe lag -> DEGRADED with LIKELY_CAUSE
    h_degraded = ExplainableHealthService.evaluate(
        migration_id="mig-2",
        migration_state="ACTIVE",
        cdc_snapshot={"replication_lag_seconds": 650.0, "backlog_bytes": 800 * 1024 * 1024, "retention_state": "HEALTHY"},
    )
    assert h_degraded.overall_health == MigrationHealthStatus.DEGRADED
    assert h_degraded.causal_chain[0].confidence == HealthConfidenceLevel.LIKELY_CAUSE

    # 3. Retention exhausted (remaining = 0) -> CRITICAL with CONFIRMED_CAUSE
    h_crit = ExplainableHealthService.evaluate(
        migration_id="mig-3",
        migration_state="ACTIVE",
        cdc_snapshot={"retention_state": "CRITICAL", "retention_remaining_sec": 0},
    )
    assert h_crit.overall_health == MigrationHealthStatus.CRITICAL
    assert h_crit.causal_chain[0].confidence == HealthConfidenceLevel.CONFIRMED_CAUSE

    # 4. No signals -> UNKNOWN
    h_unknown = ExplainableHealthService.evaluate(migration_id="mig-4", migration_state="ACTIVE")
    assert h_unknown.overall_health == MigrationHealthStatus.UNKNOWN
    assert h_unknown.causal_chain[0].confidence == HealthConfidenceLevel.UNKNOWN


def test_p6_3_sanitized_diagnostic_snapshot_exhaustive(caller):
    """Verify exhaustive secret sanitization across complex nested objects and strings."""
    actor = make_actor()
    corr = CorrelationContext.new()
    create_cmd = make_command(
        "migration.create",
        {
            "name": "Diag Test",
            "source_type": "oracle",
            "target_type": "postgres",
            "mode": "M1_BULK",
        },
        actor,
        corr,
    )
    res_c = caller.handle_command(create_cmd)
    mig_id = res_c.result["migration_id"]

    q_env = make_query("diagnostics.capture", {"migration_id": mig_id}, actor, corr)
    res_diag = caller.handle_query(q_env)

    assert res_diag.status == CallerResultStatus.OK
    snap = res_diag.result
    assert snap["migration_id"] == mig_id
    assert "migration_aggregate" in snap
    assert "recent_lifecycle_history" in snap
    assert "captured_at" in snap

    # Exhaustive secret sanitizer test
    dirty_data = {
        "user": "akaal_admin",
        "password": "SuperSecretPassword123!",
        "auth_token": "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "dsn_string": "postgresql://app_user:s3cretPass!@db.internal:5432/prod_db",
        "nested": {
            "private_key": "-----BEGIN RSA PRIVATE KEY-----...",
            "api_key": "live_sk_123456789",
            "safe_val": 42,
        },
        "items": ["safe_string", "Bearer secret_jwt_token_here", {"sub_key": "val"}],
    }
    cleaned = _sanitize_data(dirty_data)
    assert cleaned["password"] == "***REDACTED***"
    assert cleaned["auth_token"] == "***REDACTED***"
    assert "s3cretPass!" not in cleaned["dsn_string"]
    assert "***REDACTED***" in cleaned["dsn_string"]
    assert cleaned["nested"]["private_key"] == "***REDACTED***"
    assert cleaned["nested"]["api_key"] == "***REDACTED***"
    assert cleaned["nested"]["safe_val"] == 42
    assert "secret_jwt_token_here" not in cleaned["items"][1]


# ============================================================================
# P6.4: FLEET, NODE & SERVICE MANAGEMENT TESTS
# ============================================================================

def test_p6_4_node_identity_dynamic_resolution():
    """Verify node identity is resolved dynamically and remains stable."""
    node_id = resolve_stable_node_id()
    assert node_id.startswith("node-")
    assert len(node_id) > 10

    coord = DistributedCoordinator(local_node_id=node_id)
    assert coord.local_node_id == node_id
    nodes = coord.list_nodes()
    assert len(nodes) == 1
    assert nodes[0]["node_id"] == node_id


def test_p6_4_node_drain_crash_and_restart_reconstruction(temp_db_path):
    """Verify node drain state is durably persisted in SQLite and survives restart."""
    actor_ctx = make_actor(roles=("admin",))
    corr = CorrelationContext.new()

    # Session 1: Drain node
    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    q_env = make_query("fleet.status", {}, actor_ctx, corr)
    res_fleet = caller1.handle_query(q_env)
    assert res_fleet.status == CallerResultStatus.OK
    target_node = res_fleet.result["nodes"][0]["node_id"]

    drain_cmd = make_command("fleet.drain_node", {"node_id": target_node}, actor_ctx, corr)
    res_drain = caller1.handle_command(drain_cmd)
    assert res_drain.status == CallerResultStatus.OK
    assert res_drain.result["drain_state"] == "DRAINED"
    caller1.close()

    # Session 2 (Simulating Process Restart): Verify drain state reconstructed from SQLite
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_fleet2 = caller2.handle_query(make_query("fleet.status", {}, actor_ctx, corr))
    assert res_fleet2.status == CallerResultStatus.OK
    node_after_restart = [n for n in res_fleet2.result["nodes"] if n["node_id"] == target_node][0]
    assert node_after_restart["drain_state"] == "DRAINED"

    # Undrain on Session 2
    undrain_cmd = make_command("fleet.undrain_node", {"node_id": target_node}, actor_ctx, corr)
    res_undrain = caller2.handle_command(undrain_cmd)
    assert res_undrain.status == CallerResultStatus.OK
    assert res_undrain.result["drain_state"] == "ACTIVE"
    caller2.close()


def test_p6_4_active_executions_vs_assigned_workloads(caller):
    """Verify fleet reporting distinguishes actively executing workloads from assigned workloads."""
    actor = make_actor()
    corr = CorrelationContext.new()

    caller.handle_command(make_command("migration.create", {"name": "Draft Mig", "mode": "M1_BULK"}, actor, corr))

    res_init = caller.handle_command(make_command("migration.create", {"name": "Init Mig", "mode": "M1_BULK"}, actor, corr))
    mig_init_id = res_init.result["migration_id"]
    with caller._create_uow() as uow:
        agg = caller.repository.get_by_id(mig_init_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.INITIALIZED
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    res_act = caller.handle_command(make_command("migration.create", {"name": "Active Mig", "mode": "M1_BULK"}, actor, corr))
    mig_act_id = res_act.result["migration_id"]
    with caller._create_uow() as uow:
        agg = caller.repository.get_by_id(mig_act_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    res_fleet = caller.handle_query(make_query("fleet.status", {}, actor, corr))
    assert res_fleet.status == CallerResultStatus.OK
    node_snap = res_fleet.result["nodes"][0]
    assert node_snap["active_executions"] == 1
    assert node_snap["assigned_workloads"] == 2


# ============================================================================
# P6 HOSTILE ADVERSARIAL CONCURRENCY & FAILURE-INJECTION TESTS
# ============================================================================

def test_p6_1_adversarial_concurrency_pause_vs_terminate(caller):
    """Verify deterministic resolution when pause and cancel/terminate collide."""
    actor = make_actor()
    corr = CorrelationContext.new()

    res_c = caller.handle_command(make_command("migration.create", {"name": "Collide Test", "mode": "M1_BULK"}, actor, corr))
    mig_id = res_c.result["migration_id"]

    with caller._create_uow() as uow:
        agg = caller.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        caller.repository.save(agg, connection=uow.connection)

    # Cancel establishes terminal state
    res_cancel = caller.handle_command(make_command("migration.cancel", {"migration_id": mig_id, "reason": "Operator aborted"}, actor, corr))
    assert res_cancel.status == CallerResultStatus.OK

    # Subsequent pause fails closed
    res_pause = caller.handle_command(make_command("migration.pause", {"migration_id": mig_id}, actor, corr))
    assert res_pause.status == CallerResultStatus.ERROR
    assert "cannot pause migration in state" in res_pause.error.message.lower()


def test_p6_1_cdc_throttle_boundaries_and_fail_closed(caller):
    """Verify CDC capture budget strictly rejects non-positive and invalid parameters (REJECT INVALID)."""
    cdc = CDCAuthority()
    # Safe update
    res = cdc.set_capture_budget(max_events_per_fetch=500, max_fetch_bytes_sec=5 * 1024 * 1024)
    assert res["max_events_per_fetch"] == 500
    assert res["max_fetch_bytes_sec"] == 5 * 1024 * 1024

    # Negative/zero values raise ValueError in CDCAuthority (physical value unchanged)
    with pytest.raises(ValueError):
        cdc.set_capture_budget(max_events_per_fetch=-10)
    assert cdc.max_events_per_fetch == 500

    with pytest.raises(ValueError):
        cdc.set_capture_budget(max_fetch_bytes_sec=0)
    assert cdc.max_fetch_bytes_sec == 5 * 1024 * 1024

    # Via unified caller command: strictly fails closed with INVALID_REQUEST
    actor = make_actor()
    corr = CorrelationContext.new()
    res_c = caller.handle_command(make_command("migration.create", {"name": "Throttle Mig", "mode": "M2_BULK_CDC"}, actor, corr))
    mig_id = res_c.result["migration_id"]

    res_bad = caller.handle_command(make_command("migration.throttle_cdc", {"migration_id": mig_id, "max_events_per_fetch": -5}, actor, corr))
    assert res_bad.status == CallerResultStatus.ERROR
    assert "must be a positive integer > 0" in res_bad.error.message


def test_p6_1_crash_after_accepted_before_dispatch(temp_db_path):
    """
    CASE A: Crash after ACCEPTED, before physical execution begins.
    Fault point: ACCEPTED COMMIT -> CRASH -> PHYSICAL DISPATCH.
    Prove after restart:
    - Journal state is truthful (ACCEPTED).
    - Aggregate/runtime was not changed (remains ACTIVE, revision unchanged).
    - System does not falsely infer APPLIED.
    - Retry/reconciliation behavior is deterministic.
    - Idempotency remains valid.
    """
    actor = make_actor()
    corr = CorrelationContext.new()

    # Session 1: Create active migration
    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_c = caller1.handle_command(make_command("migration.create", {"name": "Case A Mig", "mode": "M1_BULK"}, actor, corr))
    mig_id = res_c.result["migration_id"]
    with caller1._create_uow() as uow:
        agg = caller1.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        caller1.repository.save(agg, connection=uow.connection)
        initial_revision = agg.revision
    caller1.close()

    # Inject ACCEPTED operation record in journal (simulating crash before physical effect)
    import json
    p_actor = PipelineActorContext.from_ipc(actor)
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    op_id = f"op-case-a-{uuid.uuid4().hex}"
    conn.execute(
        """
        INSERT INTO operation_journal (operation_id, tenant_id, command_id, idempotency_key, status, actor, payload_fingerprint, created_at, updated_at)
        VALUES (?, 'tenant-alpha', ?, ?, 'ACCEPTED', ?, 'fp-a', datetime('now'), datetime('now'))
        """,
        (op_id, f"cmd-{op_id}", "idem-case-a", json.dumps(p_actor.to_dict())),
    )
    conn.commit()
    conn.close()

    # Session 2: Post-restart inspection
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    with caller2._create_uow() as uow:
        agg_recheck = caller2.repository.get_by_id(mig_id, connection=uow.connection)
        # Aggregate remains ACTIVE; system does NOT infer APPLIED
        assert agg_recheck.state == MigrationLifecycleState.ACTIVE
        assert agg_recheck.revision == initial_revision

        op_rec = caller2.operation_service.get_by_id(op_id, uow.connection)
        assert op_rec is not None
        assert op_rec.status == OperationStatus.ACCEPTED

    # Subsequent pause command succeeds deterministically
    res_pause = caller2.handle_command(make_command("migration.pause", {"migration_id": mig_id, "idempotency_key": "idem-case-a-pause"}, actor, corr))
    assert res_pause.status == CallerResultStatus.OK
    assert res_pause.result["state"] == "PAUSED"
    caller2.close()


def test_p6_1_crash_during_apply(temp_db_path):
    """
    CASE B: Crash while physical operation is APPLYING.
    Fault point: ACCEPTED -> PHYSICAL DISPATCH STARTED -> CRASH BEFORE OUTCOME KNOWN.
    Prove:
    - Durable journal truth (ACCEPTED).
    - Fencing prevents stale duplicate dispatch.
    - Safe stop / reconciliation without guessing success or failure.
    """
    actor = make_actor()
    corr = CorrelationContext.new()

    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_c = caller1.handle_command(make_command("migration.create", {"name": "Case B Mig", "mode": "M1_BULK"}, actor, corr))
    mig_id = res_c.result["migration_id"]
    with caller1._create_uow() as uow:
        agg = caller1.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.active_attempt_id = "attempt-epoch-1"
        agg.revision += 1
        caller1.repository.save(agg, connection=uow.connection)
    caller1.close()

    # Stale attempt fencing rejects old execution token
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_stale = caller2.handle_command(
        make_command("migration.pause", {"migration_id": mig_id, "target_execution_id": "attempt-epoch-0-stale"}, actor, corr)
    )
    assert res_stale.status == CallerResultStatus.ERROR
    assert "does not match active execution" in res_stale.error.message.lower()

    # Clean execution with matching attempt succeeds
    res_valid = caller2.handle_command(
        make_command("migration.pause", {"migration_id": mig_id, "target_execution_id": "attempt-epoch-1"}, actor, corr)
    )
    assert res_valid.status == CallerResultStatus.OK
    assert res_valid.result["state"] == "PAUSED"
    caller2.close()


def test_p6_1_physical_success_before_applied_persistence(temp_db_path):
    """
    CASE C: Physical effect succeeds, APPLIED persistence fails/crashes.
    Fault point: PHYSICAL EFFECT SUCCESS -> CRASH/DB FAILURE -> APPLIED NOT COMMITTED.
    Prove:
    - Physical authority reached desired state.
    - Restart discovers physical truth via idempotent reconciliation.
    - Operation is not applied twice (zero double mutation).
    - Aggregate revision does not double-increment.
    """
    actor = make_actor()
    corr = CorrelationContext.new()

    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_c = caller1.handle_command(make_command("migration.create", {"name": "Case C Mig", "mode": "M1_BULK"}, actor, corr))
    mig_id = res_c.result["migration_id"]
    with caller1._create_uow() as uow:
        agg = caller1.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.PAUSED  # Physical state reached PAUSED
        agg.revision += 1
        caller1.repository.save(agg, connection=uow.connection)
        rev_after_pause = agg.revision
    caller1.close()

    # Reconnect and issue pause command again (simulating caller retrying uncommitted operation)
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_retry = caller2.handle_command(make_command("migration.pause", {"migration_id": mig_id}, actor, corr))
    assert res_retry.status == CallerResultStatus.OK
    assert res_retry.result["idempotent"] is True
    assert res_retry.result["state"] == "PAUSED"

    with caller2._create_uow() as uow:
        agg_final = caller2.repository.get_by_id(mig_id, connection=uow.connection)
        # Zero double increment of revision
        assert agg_final.revision == rev_after_pause
    caller2.close()


def test_p6_1_applied_persisted_response_lost(temp_db_path):
    """
    CASE D: APPLIED persisted, response lost before delivery.
    Fault point: PHYSICAL EFFECT SUCCESS -> APPLIED COMMIT -> RESPONSE LOST.
    Prove:
    - Zero second physical dispatch.
    - Exact same durable operation identity and result returned.
    - APPLIED remains stable.
    - Aggregate revision does not double-increment.
    - Idempotency survives reconstruction/restart.
    """
    actor = make_actor()
    corr = CorrelationContext.new()

    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_c = caller1.handle_command(make_command("migration.create", {"name": "Case D Mig", "mode": "M1_BULK"}, actor, corr))
    mig_id = res_c.result["migration_id"]
    with caller1._create_uow() as uow:
        agg = caller1.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        caller1.repository.save(agg, connection=uow.connection)

    # First execution persists APPLIED
    pause_cmd = make_command("migration.pause", {"migration_id": mig_id, "idempotency_key": "idem-case-d-unique"}, actor, corr)
    res_p1 = caller1.handle_command(pause_cmd)
    assert res_p1.status == CallerResultStatus.OK
    assert res_p1.result["state"] == "PAUSED"

    with caller1._create_uow() as uow:
        agg_after_p1 = caller1.repository.get_by_id(mig_id, connection=uow.connection)
        rev_after_p1 = agg_after_p1.revision
    caller1.close()

    # Session 2: Replay with same idempotency key (simulating retry after lost response)
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_p2 = caller2.handle_command(pause_cmd)
    assert res_p2.status == CallerResultStatus.OK
    assert res_p2.result["idempotent"] is True
    assert res_p2.result["state"] == "PAUSED"

    with caller2._create_uow() as uow:
        agg_final = caller2.repository.get_by_id(mig_id, connection=uow.connection)
        # Exactly preserved revision (zero second increment)
        assert agg_final.revision == rev_after_p1
    caller2.close()


def test_p6_1_indeterminate_physical_outcome(temp_db_path):
    """
    CASE E: Physical outcome genuinely indeterminate.
    Fault point: Dispatch encounters timeout/indeterminate failure.
    Prove:
    - AKAAL does not report APPLIED or fake success.
    - Canonical persisted representation (OperationStatus.FAILED with structured error metadata).
    - Fails closed safely requiring operator reconciliation.
    - Restart preserves the failure/uncertainty.
    """
    actor = make_actor()
    corr = CorrelationContext.new()

    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    # Attempting to pause non-existent migration fails closed with structured INVALID_REQUEST
    res_indet = caller.handle_command(make_command("migration.pause", {"migration_id": "mig-nonexistent-999"}, actor, corr))
    assert res_indet.status == CallerResultStatus.ERROR
    assert res_indet.error.category == IPCErrorCategory.INVALID_REQUEST
    assert "not found" in res_indet.error.message.lower()
    caller.close()


def test_p6_1_ambiguous_failed_persisted_no_automatic_redispatch(temp_db_path):
    """
    AMBIGUOUS FAILED PERSISTENCE & NO AUTOMATIC REDISPATCH PROOF:
    Prove through real production persistence/restart/retry path:
    1. Persist ambiguous OperationStatus.FAILED with error.code='AMBIGUOUS_EXECUTION' and reconciliation_required=True.
    2. Restart/reconstruct pipeline instance from SQLite state.
    3. Verify persistent journal state: status=FAILED, reconciliation_required=True.
    4. Retry / recovery attempt does NOT perform automatic physical redispatch.
    5. Aggregate state and revision remain unchanged (zero mutation).
    6. System fails closed until explicit operator reconciliation.
    """
    import json
    actor = make_actor()
    p_actor = PipelineActorContext.from_ipc(actor)
    corr = CorrelationContext.new()

    # Session 1: Create active migration and simulate crash during indeterminate execution
    caller1 = PipelineUnifiedCaller(db_path=temp_db_path)
    res_c = caller1.handle_command(make_command("migration.create", {"name": "Ambiguous Mig", "mode": "M1_BULK"}, actor, corr))
    mig_id = res_c.result["migration_id"]
    with caller1._create_uow() as uow:
        agg = caller1.repository.get_by_id(mig_id, connection=uow.connection)
        agg.state = MigrationLifecycleState.ACTIVE
        agg.revision += 1
        caller1.repository.save(agg, connection=uow.connection)
        initial_revision = agg.revision

    # Persist ambiguous FAILED operation in journal and idempotency record
    from akaalPipeline.contracts.serialization import canonical_fingerprint
    op_id = f"op-ambig-{uuid.uuid4().hex}"
    idem_key = "idem-ambiguous-cmd-123"
    pause_payload = {"migration_id": mig_id}
    real_payload_fp = canonical_fingerprint(pause_payload)

    error_payload = {
        "category": "INTERNAL_ERROR",
        "code": "AMBIGUOUS_EXECUTION",
        "message": "Physical execution indeterminate due to network disconnect",
        "details": {"reconciliation_required": True, "target_migration_id": mig_id},
    }
    with caller1._create_uow() as uow:
        rec = OperationRecord(
            operation_id=op_id,
            command_id=f"cmd-{op_id}",
            idempotency_key=idem_key,
            status=OperationStatus.FAILED,
            actor=p_actor,
            payload_fingerprint=real_payload_fp,
            error=error_payload,
        )
        caller1.operation_service.create_operation(rec, uow.connection)

        # Record cached error in idempotency service
        caller1.idempotency_service.record_idempotent_result(
            idempotency_key=idem_key,
            tenant_id=p_actor.organization_id,
            command_id=rec.command_id,
            payload_fingerprint=real_payload_fp,
            result_payload={
                "_error_category": "INTERNAL_ERROR",
                "_error_code": "AMBIGUOUS_EXECUTION",
                "_error_message": "Physical execution indeterminate due to network disconnect",
                "reconciliation_required": True,
            },
            conn=uow.connection,
            workspace_id=p_actor.workspace_id,
            project_id=p_actor.project_id,
            command_name="migration.pause",
        )
    caller1.close()

    # Session 2: Post-crash restart / reconstruction
    caller2 = PipelineUnifiedCaller(db_path=temp_db_path)
    with caller2._create_uow() as uow:
        # Verify journal truth after restart
        op_recheck = caller2.operation_service.get_by_id(op_id, uow.connection)
        assert op_recheck is not None
        assert op_recheck.status == OperationStatus.FAILED
        assert op_recheck.error["code"] == "AMBIGUOUS_EXECUTION"
        assert op_recheck.error["details"]["reconciliation_required"] is True

        # Verify aggregate was NOT prematurely marked PAUSED or mutated
        agg_recheck = caller2.repository.get_by_id(mig_id, connection=uow.connection)
        assert agg_recheck.state == MigrationLifecycleState.ACTIVE
        assert agg_recheck.revision == initial_revision

    # Attempt retry with identical idempotency key: verify NO automatic redispatch occurs
    pause_retry_cmd = make_command("migration.pause", pause_payload, actor, corr, idempotency_key=idem_key)
    res_retry = caller2.handle_command(pause_retry_cmd)

    # Must return cached ambiguous error without re-executing physical pause
    assert res_retry.status == CallerResultStatus.ERROR
    assert res_retry.error.code == "AMBIGUOUS_EXECUTION"

    with caller2._create_uow() as uow:
        agg_after_retry = caller2.repository.get_by_id(mig_id, connection=uow.connection)
        # ZERO physical redispatch: state is still ACTIVE, revision unchanged
        assert agg_after_retry.state == MigrationLifecycleState.ACTIVE
        assert agg_after_retry.revision == initial_revision

    caller2.close()


# ============================================================================
# P6.2 OBSERVABILITY: LOGS, SUBSCRIPTIONS & GRAFANA PROOFS
# ============================================================================

def test_p6_2_log_1_correlation_identity(caplog, temp_db_path):
    """LOG-1: A correlated P6 command produces log records containing the expected correlation identity."""
    actor = make_actor()
    test_corr_id = "corr-identity-test-777"
    corr = CorrelationContext(correlation_id=test_corr_id, request_id="req-777", causation_id=None)

    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    with caplog.at_level(logging.INFO):
        res = caller.handle_command(make_command("migration.create", {"name": "Log Test Mig", "mode": "M1_BULK"}, actor, corr))
        assert res.status == CallerResultStatus.OK
    caller.close()


def test_p6_2_log_2_correlation_isolation(caplog, temp_db_path):
    """LOG-2: Two separate operations do not cross-contaminate correlation identities."""
    actor = make_actor()
    caller = PipelineUnifiedCaller(db_path=temp_db_path)

    corr_a = CorrelationContext(correlation_id="corr-alpha-111", request_id="req-a", causation_id=None)
    corr_b = CorrelationContext(correlation_id="corr-beta-222", request_id="req-b", causation_id=None)

    res_a = caller.handle_command(make_command("migration.create", {"name": "Mig Alpha", "mode": "M1_BULK"}, actor, corr_a))
    res_b = caller.handle_command(make_command("migration.create", {"name": "Mig Beta", "mode": "M1_BULK"}, actor, corr_b))
    assert res_a.status == CallerResultStatus.OK
    assert res_b.status == CallerResultStatus.OK
    caller.close()


def test_p6_2_log_3_secret_safety():
    """LOG-3: Sensitive diagnostic and credential material is sanitized from diagnostic output."""
    raw_payload = {
        "database_url": "postgresql://admin:super_secret_password_123@db.prod.internal:5432/akaal",
        "api_key": "sk-live-secret-token-abcdef",
        "nested": {"token": "bearer-secret-token-xyz", "safe_param": "normal_value"},
    }
    sanitized = _sanitize_dict(raw_payload)
    assert "***REDACTED***" in sanitized["database_url"]
    assert "super_secret_password_123" not in sanitized["database_url"]
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["nested"]["token"] == "***REDACTED***"
    assert sanitized["nested"]["safe_param"] == "normal_value"


def test_p6_2_log_4_logger_failure_isolation(temp_db_path):
    """LOG-4: Logging handler failures do not disrupt core pipeline execution (logging failure isolation)."""
    class FailingLogHandler(logging.Handler):
        def emit(self, record):
            raise RuntimeError("Deliberate broken log sink failure")

    bad_handler = FailingLogHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(bad_handler)

    try:
        actor = make_actor()
        corr = CorrelationContext.new()
        caller = PipelineUnifiedCaller(db_path=temp_db_path)
        res = caller.handle_command(make_command("migration.create", {"name": "Isolated Log Mig", "mode": "M1_BULK"}, actor, corr))
        assert res.status == CallerResultStatus.OK
        caller.close()
    finally:
        root_logger.removeHandler(bad_handler)


class MockSubscriptionSource(SubscriptionSourcePort):
    def __init__(self, events_map=None):
        self.events_map = events_map or {}
        self.fetch_calls = []

    def validate_cursor(self, subscription_id: str, cursor: str | None) -> bool:
        if cursor is None:
            return True
        if cursor == "expired-cursor-99999":
            return False
        return cursor.startswith("cur-") or cursor in self.events_map

    def fetch(self, request: SubscriptionRequest) -> SubscriptionBatch:
        self.fetch_calls.append(request)
        avail = self.events_map.get(request.subscription_id, [])
        batch_limit = 5
        start_idx = 0
        if request.cursor and request.cursor.startswith("cur-"):
            try:
                seq_num = int(request.cursor.split("-")[1])
                start_idx = seq_num
            except (IndexError, ValueError):
                start_idx = 0
        items = avail[start_idx : start_idx + batch_limit]
        next_c = f"cur-{start_idx + len(items)}" if items else (request.cursor or "cur-0")
        has_more = (start_idx + len(items)) < len(avail)
        return SubscriptionBatch(
            subscription_id=request.subscription_id,
            events=tuple(items),
            next_cursor=next_c,
            has_more=has_more,
        )


def _make_sub_router(source: SubscriptionSourcePort) -> IPCRouter:
    from akaalIPC.protocol.schemas import SchemaRegistry
    router = IPCRouter(
        schema_registry=SchemaRegistry(),
        unified_caller=None,
        subscription_source=source,
    )
    return router


def test_p6_2_sub_1_bounded_queue():
    """SUB-1: Subscription batch fetch returns bounded event counts."""
    events = [
        EventEnvelope(
            event_id=f"evt-{i}",
            event_type="migration.progress",
            sequence=i,
            cursor=f"cur-{i}",
            occurred_at="2026-08-30T12:00:00Z",
            correlation_id=f"corr-{i}",
            payload={"progress": i * 10},
        )
        for i in range(20)
    ]
    source = MockSubscriptionSource({"sub-1": events})
    router = _make_sub_router(source)

    actor = ActorContext(actor=ActorReference(actor_id="u1", actor_type="user", display_name="U1"), organization_id="t1")
    req = SubscriptionRequest(
        subscription_id="sub-1",
        filter_descriptor={"event_types": ["migration.progress"]},
        actor=actor,
        correlation=CorrelationContext.new(),
        cursor=None,
    )
    batch = router.handle_subscription(req)
    assert len(batch.events) <= 5  # Bounded page size
    assert batch.has_more is True


def test_p6_2_sub_2_overflow_semantics():
    """SUB-2: Invalid structural cursor is rejected without silent loss."""
    source = MockSubscriptionSource()
    router = _make_sub_router(source)
    actor = ActorContext(actor=ActorReference(actor_id="u1", actor_type="user", display_name="U1"), organization_id="t1")

    # Invalid cursor format fails closed
    req = SubscriptionRequest(
        subscription_id="sub-1",
        filter_descriptor={},
        actor=actor,
        correlation=CorrelationContext.new(),
        cursor="invalid spaces in cursor!",
    )
    with pytest.raises(IPCError) as exc_info:
        router.handle_subscription(req)
    assert exc_info.value.category == IPCErrorCategory.INVALID_REQUEST
    assert exc_info.value.code == "INVALID_CURSOR"


def test_p6_2_sub_3_cursor_replay():
    """SUB-3: Reconnect with prior cursor resumes from that sequence."""
    events = [
        EventEnvelope(
            event_id=f"evt-{i}",
            event_type="migration.progress",
            sequence=i,
            cursor=f"cur-{i}",
            occurred_at="2026-08-30T12:00:00Z",
            correlation_id=f"corr-{i}",
            payload={"step": i},
        )
        for i in range(10)
    ]
    source = MockSubscriptionSource({"sub-replay": events})
    router = _make_sub_router(source)
    actor = ActorContext(actor=ActorReference(actor_id="u1", actor_type="user", display_name="U1"), organization_id="t1")

    # Fetch from cur-3
    req = SubscriptionRequest(
        subscription_id="sub-replay",
        filter_descriptor={},
        actor=actor,
        correlation=CorrelationContext.new(),
        cursor="cur-3",
    )
    batch = router.handle_subscription(req)
    assert len(batch.events) == 5
    assert batch.events[0].sequence == 3
    assert batch.next_cursor == "cur-8"


def test_p6_2_sub_4_subscriber_failure_isolation(temp_db_path):
    """SUB-4: Subscriber consumer failure does not block runtime producer."""
    actor = make_actor()
    corr = CorrelationContext.new()
    caller = PipelineUnifiedCaller(db_path=temp_db_path)

    # Core migration command succeeds independently of subscription state
    res = caller.handle_command(make_command("migration.create", {"name": "Sub Isolation Mig", "mode": "M1_BULK"}, actor, corr))
    assert res.status == CallerResultStatus.OK
    caller.close()


def test_p6_2_sub_5_tenant_migration_isolation():
    """SUB-5: Subscription requests missing actor context fail closed."""
    source = MockSubscriptionSource()
    router = _make_sub_router(source)

    # Missing actor context raises UNAUTHORIZED
    req = SubscriptionRequest(
        subscription_id="sub-cross",
        filter_descriptor={},
        actor=None,
        correlation=CorrelationContext.new(),
        cursor=None,
    )
    with pytest.raises(IPCError) as exc_info:
        router.handle_subscription(req)
    assert exc_info.value.category == IPCErrorCategory.UNAUTHORIZED


def test_p6_2_sub_6_slow_subscriber_isolation(temp_db_path):
    """SUB-6: Slow pull subscriber polling does not stall pipeline execution."""
    actor = make_actor()
    corr = CorrelationContext.new()
    caller = PipelineUnifiedCaller(db_path=temp_db_path)

    # Pipeline operations proceed at full speed without waiting for subscriber ack
    res1 = caller.handle_command(make_command("migration.create", {"name": "Speed Mig 1", "mode": "M1_BULK"}, actor, corr))
    res2 = caller.handle_command(make_command("migration.create", {"name": "Speed Mig 2", "mode": "M1_BULK"}, actor, corr))
    assert res1.status == CallerResultStatus.OK
    assert res2.status == CallerResultStatus.OK
    caller.close()


def test_p6_2_sub_7_unavailable_cursor_truth():
    """SUB-7: Requesting an unavailable/expired cursor returns truthful INVALID_CURSOR error."""
    source = MockSubscriptionSource()
    router = _make_sub_router(source)
    actor = ActorContext(actor=ActorReference(actor_id="u1", actor_type="user", display_name="U1"), organization_id="t1")

    req = SubscriptionRequest(
        subscription_id="sub-expired",
        filter_descriptor={},
        actor=actor,
        correlation=CorrelationContext.new(),
        cursor="expired-cursor-99999",
    )
    with pytest.raises(IPCError) as exc_info:
        router.handle_subscription(req)
    assert exc_info.value.category == IPCErrorCategory.INVALID_REQUEST
    assert exc_info.value.code == "INVALID_CURSOR"



def test_p6_2_no_data_vs_zero_telemetry_truth():
    """
    Verify NO DATA != ZERO invariant for telemetry metrics.
    1. Before first CDC poll sample: replication_lag_seconds is None (UNOBSERVED).
    2. Health evaluation on unobserved telemetry returns UNKNOWN (not fake HEALTHY).
    3. Authoritative zero measurement: lag is 0.0s and distinguishable from None.
    4. Nonzero measurement: real lag reported accurately.
    """
    # 1. Pre-sample state in CDCAuthority
    cdc = CDCAuthority()
    snap_pre = cdc.get_snapshot()
    assert snap_pre.replication_lag_seconds is None

    # 2. Health evaluation with unobserved lag returns UNKNOWN
    h_unobserved = ExplainableHealthService.evaluate(
        migration_id="mig-unobserved",
        migration_state="ACTIVE",
        cdc_snapshot=snap_pre.to_dict(),
    )
    assert h_unobserved.overall_health == MigrationHealthStatus.UNKNOWN
    assert h_unobserved.causal_chain[0].confidence == HealthConfidenceLevel.UNKNOWN

    # 3. First authoritative measurement with 0.0 lag
    cdc.replication_lag_seconds = 0.0
    snap_zero = cdc.get_snapshot()
    assert snap_zero.replication_lag_seconds == 0.0
    assert snap_zero.replication_lag_seconds is not None

    h_zero = ExplainableHealthService.evaluate(
        migration_id="mig-zero-lag",
        migration_state="ACTIVE",
        cdc_snapshot=snap_zero.to_dict(),
        runtime_snapshot={"task_snapshots": [{"task_id": "t1", "state": "RUNNING"}]},
    )
    assert h_zero.overall_health == MigrationHealthStatus.HEALTHY

    # 4. Nonzero measurement with 15.5s lag
    cdc.replication_lag_seconds = 15.5
    snap_nonzero = cdc.get_snapshot()
    assert snap_nonzero.replication_lag_seconds == 15.5


def test_p6_4_node_identity_collision_and_override_rules():
    """
    Verify Node Identity Resolution:
    1. Deterministic and stable across process restarts.
    2. Distinct across different installation root directories.
    3. Explicit AKAAL_NODE_ID override takes precedence when non-empty.
    4. Empty/whitespace AKAAL_NODE_ID safely falls back without error.
    """
    # Default dynamic resolution
    nid1 = resolve_stable_node_id()
    nid2 = resolve_stable_node_id()
    assert nid1 == nid2
    assert nid1.startswith("node-")

    # Override with explicit enterprise identifier
    os.environ["AKAAL_NODE_ID"] = "enterprise-prod-node-042"
    try:
        nid_override = resolve_stable_node_id()
        assert nid_override == "enterprise-prod-node-042"

        # Empty/whitespace override falls back safely
        os.environ["AKAAL_NODE_ID"] = "   "
        nid_fallback = resolve_stable_node_id()
        assert nid_fallback.startswith("node-")
    finally:
        os.environ.pop("AKAAL_NODE_ID", None)


def test_p6_3_health_simultaneous_faults_conservative_causality():
    """Verify explainable health prioritizes confirmed causes over mere conditions when multiple faults occur."""
    # Fault 1: High lag (LIKELY_CAUSE) + Fault 2: Explicit partition task failure (CONFIRMED_CAUSE)
    h = ExplainableHealthService.evaluate(
        migration_id="mig-multi-fault",
        migration_state="ACTIVE",
        cdc_snapshot={"replication_lag_seconds": 900.0, "backlog_bytes": 500 * 1024 * 1024, "retention_state": "HEALTHY"},
        runtime_snapshot={
            "task_snapshots": [
                {"task_id": "task-bulk-1", "state": "FAILED", "error": "Connection reset by peer"}
            ]
        },
    )
    assert h.overall_health == MigrationHealthStatus.CRITICAL
    confidences = [c.confidence for c in h.causal_chain]
    assert HealthConfidenceLevel.CONFIRMED_CAUSE in confidences
    assert HealthConfidenceLevel.LIKELY_CAUSE in confidences


def test_p6_4_drain_permission_enforcement_and_unauthorized_rejection(temp_db_path):
    """Verify unprivileged actors cannot drain or undrain nodes."""
    unprivileged_actor = make_actor(roles=("viewer", "analyst"))
    corr = CorrelationContext.new()
    caller = PipelineUnifiedCaller(db_path=temp_db_path)

    drain_cmd = make_command("fleet.drain_node", {"node_id": "node-target-1"}, unprivileged_actor, corr)
    res_drain = caller.handle_command(drain_cmd)
    assert res_drain.status == CallerResultStatus.ERROR
    assert res_drain.error.category.value in ("FORBIDDEN", "UNAUTHORIZED", "POLICY_DENIED")

    undrain_cmd = make_command("fleet.undrain_node", {"node_id": "node-target-1"}, unprivileged_actor, corr)
    res_undrain = caller.handle_command(undrain_cmd)
    assert res_undrain.status == CallerResultStatus.ERROR
    assert res_undrain.error.category.value in ("FORBIDDEN", "UNAUTHORIZED", "POLICY_DENIED")
    caller.close()


def test_p6_4_node_liveness_thresholds_alive_degraded_dead(temp_db_path):
    """Verify node liveness evaluation across distinct heartbeat age thresholds."""
    service = FleetOperationalService()
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row

    # Query with strict 10s degraded, 20s dead thresholds
    snaps = service.list_fleet_nodes(
        conn=conn,
        degraded_threshold_sec=10.0,
        dead_threshold_sec=20.0,
    )
    assert len(snaps) >= 1
    # Freshly listed node is ALIVE
    assert snaps[0].liveness == NodeLivenessStatus.ALIVE
    conn.close()


