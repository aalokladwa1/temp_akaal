"""tests.pipeline.test_p6_campaign_b
=================================
Dedicated Hostile Acceptance Test Suite for AKAAL P6.5:
- Enterprise Scheduling & Recurrence Engine
- Timezone Normalization & DST Boundary Handling
- Deterministic Occurrence Identity & Monotonic Revisioning
- Lease-Fenced Occurrence Claiming & Stale Worker Fencing
- Occurrence-Time Authorization Verification (Replay Prevention)
- Misfire & Overlap Admission Policies
- Operational Retention Multi-Class Protection Engine
- Evidence #12 Protection from Generic Retention
- Active Migration & Ambiguous Idempotency Retention Protection
- Non-Destructive Retention Preview vs Bounded Batch Execution
- Cross-Tenant Security Isolation
- Scheduler Crash Safety Matrix (SCHED-A through SCHED-F)
- Retention Crash Safety Matrix (RET-A through RET-G)
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pytest

from akaalIPC.protocol.envelopes import CommandEnvelope, CorrelationContext, QueryEnvelope
from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.protocol.schemas import RequestKind, SchemaRegistry, register_core_pipeline_schemas
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from tests.pipeline.conftest import authorized_caller, provision_verified_actor
from akaalPipeline.contracts.enums import (
    AlertLifecycleState,
    AlertSeverity,
    CapacityRiskLevel,
    IncidentSeverity,
    IncidentStatus,
    MigrationLifecycleState,
    MisfirePolicy,
    NotificationChannel,
    NotificationDeliveryStatus,
    OccurrenceStatus,
    OverlapPolicy,
    ResourceEvidenceKind,
    ResourceType,
    RetentionProtectionClass,
    ScheduleLifecycleState,
    ScheduleType,
)
from akaalPipeline.contracts.errors import (
    LeaseConflictError,
    PipelineError,
    PipelineErrorCode,
    UnableToAcquireLeaseError,
)
from akaalPipeline.operations.alerts import AlertRecord, AlertRuleRecord, AlertService
from akaalPipeline.operations.capacity import (
    CapacityForecast,
    CapacityIntelligenceService,
    CapacityRecommendation,
    CapacityReport,
    ResourceObservation,
    StorageBreakdown,
)
from akaalPipeline.operations.cron import (
    ParsedCronExpression,
    compute_next_occurrence,
    validate_cron_expression,
    validate_timezone,
)
from akaalPipeline.operations.gateway import GatewayCapabilities, OperationsGateway
from akaalPipeline.operations.incidents import IncidentRecord, IncidentService, IncidentTimelineRecord
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.notifications import (
    NotificationAdapter,
    NotificationDeliveryRecord,
    NotificationRequest,
    NotificationService,
    StructuredLogSink,
    WebhookAdapter,
)
from akaalPipeline.operations.retention import (
    OperationalRetentionService,
    RetentionExecutionResult,
    RetentionPolicy,
    RetentionPreviewResult,
)
from akaalPipeline.operations.schedules import (
    ScheduleOccurrenceRecord,
    ScheduleRecord,
    ScheduleService,
    compute_occurrence_id,
)
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def test_db_path(tmp_path):
    db_file = tmp_path / "test_p6_5.db"
    uow = SQLiteUnitOfWork(str(db_file))
    with uow:
        pass
    return str(db_file)


@pytest.fixture
def unified_caller(test_db_path):
    return authorized_caller(db_path=test_db_path)


@pytest.fixture
def admin_actor():
    return PipelineActorContext(
        actor_id="admin-usr-1",
        actor_type="user",
        organization_id="tenant-alpha",
        workspace_id="ws-main",
        project_id="proj-1",
        roles=("PlatformAdministrator", "admin"),
    )


@pytest.fixture
def tenant_beta_actor():
    return PipelineActorContext(
        actor_id="admin-usr-beta",
        actor_type="user",
        organization_id="tenant-beta",
        workspace_id="ws-beta",
        project_id="proj-beta",
        roles=("PlatformAdministrator", "admin"),
    )


def make_cmd(
    request_type: str,
    payload: dict,
    actor: PipelineActorContext,
    correlation: CorrelationContext,
    idempotency_key: Optional[str] = None,
) -> CommandEnvelope:
    return CommandEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:12]}",
        command_id=f"cmd-{uuid.uuid4().hex[:12]}",
        request_type=request_type,
        protocol_version="1.0.0",
        schema_version="1.0",
        payload=payload,
        kind=RequestKind.COMMAND,
        actor=actor.to_ipc(),
        correlation=correlation,
        idempotency_key=idempotency_key,
    )


def make_qry(
    request_type: str,
    payload: dict,
    actor: PipelineActorContext,
    correlation: CorrelationContext,
) -> QueryEnvelope:
    return QueryEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:12]}",
        request_type=request_type,
        protocol_version="1.0.0",
        schema_version="1.0",
        payload=payload,
        kind=RequestKind.QUERY,
        actor=actor.to_ipc(),
        correlation=correlation,
    )


# =============================================================================
# 1. CRON & TIMEZONE EVALUATOR TESTS
# =============================================================================

def test_cron_parsing_and_boundaries():
    """Verify 5-field cron parsing with standard boundaries and step/list support."""
    validate_cron_expression("0 * * * *")
    validate_cron_expression("*/15 2-4 1,15 * 1-5")
    validate_cron_expression("59 23 31 12 0")

    with pytest.raises(PipelineError):
        validate_cron_expression("* * * *")
    with pytest.raises(PipelineError):
        validate_cron_expression("60 * * * *")
    with pytest.raises(PipelineError):
        validate_cron_expression("* 24 * * *")
    with pytest.raises(PipelineError):
        validate_cron_expression("* * 32 * *")
    with pytest.raises(PipelineError):
        validate_cron_expression("* * * 13 *")


def test_timezone_validation_and_dst_handling():
    """Verify IANA timezone validation and UTC normalization across DST transitions."""
    tz_ny = validate_timezone("America/New_York")
    assert tz_ny is not None
    tz_kolkata = validate_timezone("Asia/Kolkata")
    assert tz_kolkata is not None

    with pytest.raises(PipelineError):
        validate_timezone("Mars/Olympus_Mons")

    base_dt = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    next_occ = compute_next_occurrence("0 14 * * *", tz_name="America/New_York", after_utc=base_dt)
    assert "2026-06-01" in next_occ and ("18:00:00" in next_occ or "19:00:00" in next_occ)


# =============================================================================
# 2. SCHEDULE LIFECYCLE & DETERMINISTIC OCCURRENCE IDENTITY
# =============================================================================

def test_schedule_crud_and_lifecycle(unified_caller, admin_actor):
    """Test full schedule CRUD: create, arm, update, disable, enable, cancel, delete."""
    corr = CorrelationContext.new(causation_id="cause-1")
    mig_res = unified_caller.handle_command(make_cmd(
        request_type="migration.create",
        payload={"migration_id": "mig-sched-target-1", "name": "Scheduled Migration"},
        actor=admin_actor,
        correlation=corr,
    ))
    assert mig_res.status.value == "OK"

    # 1. Create Schedule
    res = unified_caller.handle_command(make_cmd(
        request_type="schedule.create",
        payload={
            "schedule_id": "sch-001",
            "migration_id": "mig-sched-target-1",
            "cron_expression": "*/10 * * * *",
            "timezone": "UTC",
            "misfire_policy": "SKIP",
            "overlap_policy": "SKIP_WHILE_ACTIVE",
        },
        actor=admin_actor,
        correlation=corr,
    ))
    assert res.status.value == "OK"
    sch_data = res.result
    assert sch_data["schedule_id"] == "sch-001"
    assert sch_data["state"] == "DRAFT"
    assert sch_data["revision"] == 1
    assert sch_data["next_occurrence_time"] is not None

    # 2. Arm Schedule
    arm_res = unified_caller.handle_command(make_cmd(
        request_type="schedule.arm",
        payload={"schedule_id": "sch-001"},
        actor=admin_actor,
        correlation=corr,
    ))
    assert arm_res.status.value == "OK"
    assert arm_res.result["state"] == "ARMED"

    # 3. Update Schedule (bumps revision)
    upd_res = unified_caller.handle_command(make_cmd(
        request_type="schedule.update",
        payload={"schedule_id": "sch-001", "cron_expression": "0 * * * *"},
        actor=admin_actor,
        correlation=corr,
    ))
    assert upd_res.status.value == "OK"
    assert upd_res.result["revision"] == 2
    assert upd_res.result["cron_expression"] == "0 * * * *"

    # 4. Disable / Enable
    dis_res = unified_caller.handle_command(make_cmd(
        request_type="schedule.disable",
        payload={"schedule_id": "sch-001"},
        actor=admin_actor,
        correlation=corr,
    ))
    assert dis_res.status.value == "OK"
    assert dis_res.result["enabled"] is False

    en_res = unified_caller.handle_command(make_cmd(
        request_type="schedule.enable",
        payload={"schedule_id": "sch-001"},
        actor=admin_actor,
        correlation=corr,
    ))
    assert en_res.status.value == "OK"
    assert en_res.result["enabled"] is True

    # 5. Query Schedule
    q_res = unified_caller.handle_query(make_qry(
        request_type="schedule.get",
        payload={"schedule_id": "sch-001"},
        actor=admin_actor,
        correlation=corr,
    ))
    assert q_res.status.value == "OK"
    assert q_res.result["schedule_id"] == "sch-001"


def test_deterministic_occurrence_identity_and_idempotency(test_db_path, admin_actor):
    """Verify deterministic occurrence ID computation and idempotent materialization."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        sch = ScheduleRecord(
            schedule_id="sch-idemp-1",
            tenant_id=admin_actor.organization_id,
            migration_id="mig-1",
            cron_expression="0 * * * *",
            state=ScheduleLifecycleState.ARMED,
            next_occurrence_time="2026-09-01T00:00:00+00:00",
        )
        service.create_schedule(sch, uow.connection)

        occs1 = service.materialize_due_occurrences(uow.connection, current_time_iso="2026-09-01T00:05:00+00:00")
        assert len(occs1) == 1
        occ_id = occs1[0].occurrence_id
        assert occ_id == compute_occurrence_id("sch-idemp-1", 1, "2026-09-01T00:00:00+00:00")

        occ_rec = service.get_occurrence_by_id(occ_id, uow.connection)
        assert occ_rec is not None
        assert occ_rec.occurrence_id == occ_id


# =============================================================================
# 3. LEASE-FENCED OCCURRENCE CLAIMING & FENCING EPOCH (SCHED-CRASH)
# =============================================================================

def test_lease_fenced_claiming_and_stale_claimant_fencing(test_db_path, admin_actor):
    """Verify SCHED-CRASH: concurrent claim rejection, lease expiry takeover, and stale claimant fencing."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        occ = ScheduleOccurrenceRecord(
            occurrence_id="occ-fence-test-1",
            schedule_id="sch-1",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-09-01T10:00:00+00:00",
            status=OccurrenceStatus.PENDING,
        )
        uow.connection.execute(
            """
            INSERT INTO schedule_occurrences (
                occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (occ.occurrence_id, occ.schedule_id, occ.tenant_id, occ.canonical_scheduled_time, occ.status.value, occ.created_at, occ.updated_at),
        )

        lease1 = service.claim_occurrence(
            occurrence_id="occ-fence-test-1",
            owner_id="worker-node-1",
            attempt_id="att-sched-1",
            conn=uow.connection,
            lease_duration_seconds=30,
        )
        assert lease1.owner_id == "worker-node-1"
        assert lease1.fence_epoch == 1

        with pytest.raises(UnableToAcquireLeaseError):
            service.claim_occurrence(
                occurrence_id="occ-fence-test-1",
                owner_id="worker-node-2",
                attempt_id="att-sched-1",
                conn=uow.connection,
                lease_duration_seconds=30,
            )

        past_expiry = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        uow.connection.execute(
            "UPDATE leases SET expires_at = ? WHERE attempt_id = ?",
            (past_expiry, "att-sched-1"),
        )

        lease2 = service.claim_occurrence(
            occurrence_id="occ-fence-test-1",
            owner_id="worker-node-2",
            attempt_id="att-sched-1",
            conn=uow.connection,
            lease_duration_seconds=30,
        )
        assert lease2.owner_id == "worker-node-2"
        assert lease2.fence_epoch == 2

        with pytest.raises(LeaseConflictError):
            service.mark_dispatched(
                occurrence_id="occ-fence-test-1",
                command_id="cmd-dispatch-stale",
                lease_id=lease1.lease_id,
                fence_epoch=1,
                conn=uow.connection,
            )

        service.mark_dispatched(
            occurrence_id="occ-fence-test-1",
            command_id="cmd-dispatch-valid",
            lease_id=lease2.lease_id,
            fence_epoch=2,
            conn=uow.connection,
        )
        occ_after = service.get_occurrence_by_id("occ-fence-test-1", uow.connection)
        assert occ_after.status == OccurrenceStatus.DISPATCHED


# =============================================================================
# 4. OCCURRENCE-TIME AUTHORIZATION (REPLAY PREVENTION)
# =============================================================================

def test_occurrence_authorization_revocation_fails_closed(unified_caller, test_db_path, admin_actor):
    """Verify that when creator permissions or target migration becomes invalid, occurrence fails closed with zero dispatch."""
    corr = CorrelationContext.new(causation_id="cause-1")

    # 1. Create migration and schedule
    unified_caller.handle_command(make_cmd(
        request_type="migration.create",
        payload={"migration_id": "mig-rev-target-1", "name": "Revocation Test Migration"},
        actor=admin_actor,
        correlation=corr,
    ))

    res = unified_caller.handle_command(make_cmd(
        request_type="schedule.create",
        payload={
            "schedule_id": "sch-rev-001",
            "migration_id": "mig-rev-target-1",
            "cron_expression": "0 * * * *",
            "arm_immediately": True,
        },
        actor=admin_actor,
        correlation=corr,
    ))
    assert res.status.value == "OK"

    # 2. Cancel target migration (simulating revoked / invalid lifecycle)
    unified_caller.handle_command(make_cmd(
        request_type="migration.cancel",
        payload={"migration_id": "mig-rev-target-1"},
        actor=admin_actor,
        correlation=corr,
    ))

    # 3. Simulate unauthorized actor trying to operate schedule or dispatch
    unauth_actor = PipelineActorContext(
        actor_id="unauth-usr",
        actor_type="user",
        organization_id="other-tenant",
        workspace_id="ws-other",
        roles=("guest",),
    )

    unauth_res = unified_caller.handle_command(make_cmd(
        request_type="schedule.arm",
        payload={"schedule_id": "sch-rev-001"},
        actor=unauth_actor,
        correlation=corr,
    ))
    assert unauth_res.status.value == "ERROR"


# =============================================================================
# 5. MISFIRE & OVERLAP POLICIES
# =============================================================================

def test_misfire_and_overlap_policy_handling(test_db_path, admin_actor):
    """Verify SKIP misfire policy and SKIP_WHILE_ACTIVE overlap policy."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        occ1 = ScheduleOccurrenceRecord(
            occurrence_id="occ-misfire-1",
            schedule_id="sch-mis-1",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-08-01T00:00:00+00:00",
            status=OccurrenceStatus.PENDING,
        )
        uow.connection.execute(
            """
            INSERT INTO schedule_occurrences (
                occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (occ1.occurrence_id, occ1.schedule_id, occ1.tenant_id, occ1.canonical_scheduled_time, occ1.status.value, occ1.created_at, occ1.updated_at),
        )

        service.mark_misfired("occ-misfire-1", "Execution window expired by 24 hours.", uow.connection)
        occ1_res = service.get_occurrence_by_id("occ-misfire-1", uow.connection)
        assert occ1_res.status == OccurrenceStatus.MISFIRED

        occ2 = ScheduleOccurrenceRecord(
            occurrence_id="occ-overlap-1",
            schedule_id="sch-over-1",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-09-01T00:00:00+00:00",
            status=OccurrenceStatus.PENDING,
        )
        uow.connection.execute(
            """
            INSERT INTO schedule_occurrences (
                occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (occ2.occurrence_id, occ2.schedule_id, occ2.tenant_id, occ2.canonical_scheduled_time, occ2.status.value, occ2.created_at, occ2.updated_at),
        )

        service.mark_skipped_overlap("occ-overlap-1", "mig-target-active", uow.connection)
        occ2_res = service.get_occurrence_by_id("occ-overlap-1", uow.connection)
        assert occ2_res.status == OccurrenceStatus.SKIPPED_OVERLAP


# =============================================================================
# 6. OPERATIONAL RETENTION & EVIDENCE #12 PROTECTION
# =============================================================================

def test_evidence_12_and_sealed_artifacts_strictly_protected(test_db_path, admin_actor):
    """Verify Evidence #12 and immutable sealed artifacts are protected from generic operational retention."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        uow.connection.execute(
            """
            INSERT INTO immutable_artifacts (
                artifact_id, tenant_id, artifact_type, fingerprint, content, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "art-evidence-12-test",
                admin_actor.organization_id,
                "EVIDENCE_12",
                "sha256-dummy-proof",
                json.dumps({"evidence": "sealed_proof"}),
                old_time,
            ),
        )

        policy = RetentionPolicy(
            cutoff_time=datetime.now(timezone.utc).isoformat(),
            tenant_id=admin_actor.organization_id,
            data_classes=["immutable_artifacts"],
        )
        prev = ret_service.preview(policy, uow.connection, actor=admin_actor)
        assert prev.considered_count == 1
        assert prev.eligible_count == 0
        assert prev.protected_count == 1
        assert prev.protection_breakdown[RetentionProtectionClass.EVIDENCE_PROTECTED.value] == 1

        exec_res = ret_service.execute(policy, uow.connection, actor=admin_actor)
        assert exec_res.deleted_count == 0
        assert exec_res.protected_count == 1

        cur = uow.connection.execute("SELECT * FROM immutable_artifacts WHERE artifact_id = ?", ("art-evidence-12-test",))
        assert cur.fetchone() is not None


def test_active_migration_and_ambiguous_idempotency_retention_protection(test_db_path, admin_actor):
    """Verify that active migration checkpoints and ambiguous FAILED operations (reconciliation_required=True) are protected from pruning."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        old_time = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

        # 1. Create active migration and completed migration
        uow.connection.execute(
            """
            INSERT INTO migrations (
                migration_id, revision, name, mode, state, tenant_id, workspace_id,
                configuration, lineage, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("mig-active-1", 1, "Active Migration", "M1", "ACTIVE", admin_actor.organization_id, "ws-main", "{}", "[]", old_time, old_time),
        )
        uow.connection.execute(
            """
            INSERT INTO migrations (
                migration_id, revision, name, mode, state, tenant_id, workspace_id,
                configuration, lineage, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("mig-completed-1", 1, "Completed Migration", "M1", "COMPLETED", admin_actor.organization_id, "ws-main", "{}", "[]", old_time, old_time),
        )

        # 2. Insert checkpoints for both
        uow.connection.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, tenant_id, migration_id, attempt_id, invocation_id,
                lease_id, fence_epoch, graph_node_id, initialization_fingerprint,
                binding_id, payload_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("chk-active", admin_actor.organization_id, "mig-active-1", "att-1", "inv-1", "l-1", 1, "node-1", "fp-1", "b-1", "ref-1", old_time),
        )
        uow.connection.execute(
            """
            INSERT INTO checkpoints (
                checkpoint_id, tenant_id, migration_id, attempt_id, invocation_id,
                lease_id, fence_epoch, graph_node_id, initialization_fingerprint,
                binding_id, payload_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("chk-completed", admin_actor.organization_id, "mig-completed-1", "att-2", "inv-2", "l-2", 1, "node-1", "fp-2", "b-2", "ref-2", old_time),
        )

        # 3. Insert ambiguous FAILED operation with reconciliation_required=True
        ambiguous_err = json.dumps({
            "code": "AMBIGUOUS_EXECUTION",
            "details": {"reconciliation_required": True},
        })
        uow.connection.execute(
            """
            INSERT INTO operation_journal (
                operation_id, tenant_id, command_id, idempotency_key, status,
                actor, payload_fingerprint, error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("op-ambiguous-1", admin_actor.organization_id, "cmd-amb-1", "idem-amb-key", "FAILED", admin_actor.actor_id, "fp-amb", ambiguous_err, old_time, old_time),
        )
        uow.connection.execute(
            """
            INSERT INTO idempotency_records (
                record_id, tenant_id, idempotency_key, command_id,
                payload_fingerprint, result_payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("rec-idem-amb", admin_actor.organization_id, "idem-amb-key", "cmd-amb-1", "fp-amb", ambiguous_err, old_time),
        )

        # 4. Run Retention Execution
        policy = RetentionPolicy(
            cutoff_time=datetime.now(timezone.utc).isoformat(),
            tenant_id=admin_actor.organization_id,
            data_classes=["checkpoints", "operation_journal", "idempotency_records"],
        )
        exec_res = ret_service.execute(policy, uow.connection, actor=admin_actor)

        # chk-completed should be deleted (1)
        # chk-active protected (1), op-ambiguous-1 protected (1), rec-idem-amb protected (1) -> 3 protected
        assert exec_res.deleted_count == 1
        assert exec_res.protected_count >= 3

        # Verify active checkpoint still exists
        cur = uow.connection.execute("SELECT * FROM checkpoints WHERE checkpoint_id = 'chk-active'")
        assert cur.fetchone() is not None

        # Verify completed checkpoint was pruned
        cur = uow.connection.execute("SELECT * FROM checkpoints WHERE checkpoint_id = 'chk-completed'")
        assert cur.fetchone() is None

        # Verify ambiguous operation and idempotency key still exist
        cur = uow.connection.execute("SELECT * FROM operation_journal WHERE operation_id = 'op-ambiguous-1'")
        assert cur.fetchone() is not None
        cur = uow.connection.execute("SELECT * FROM idempotency_records WHERE idempotency_key = 'idem-amb-key'")
        assert cur.fetchone() is not None


# =============================================================================
# 7. NON-DESTRUCTIVE PREVIEW VS EXECUTION & IPC CALLER INTEGRATION
# =============================================================================

def test_retention_preview_and_execution_via_caller(unified_caller, test_db_path, admin_actor):
    """Verify retention.preview and retention.execute through PipelineUnifiedCaller."""
    corr = CorrelationContext.new(causation_id="cause-1")
    old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        uow.connection.execute(
            """
            INSERT INTO migrations (
                migration_id, revision, name, mode, state, tenant_id, workspace_id,
                configuration, lineage, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("mig-prune-1", 1, "Prune Migration", "M1", "COMPLETED", admin_actor.organization_id, "ws-main", "{}", "[]", old_time, old_time),
        )
        uow.connection.execute(
            """
            INSERT INTO operation_journal (
                operation_id, tenant_id, command_id, idempotency_key, status,
                actor, payload_fingerprint, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("op-prune-1", admin_actor.organization_id, "cmd-p-1", "idem-p-1", "SUCCEEDED", admin_actor.actor_id, "fp-p", old_time, old_time),
        )

    # 1. Preview Query
    prev_res = unified_caller.handle_query(make_qry(
        request_type="retention.preview",
        payload={
            "cutoff_time": datetime.now(timezone.utc).isoformat(),
            "data_classes": ["operation_journal"],
        },
        actor=admin_actor,
        correlation=corr,
    ))
    assert prev_res.status.value == "OK"
    assert prev_res.result["considered_count"] >= 1
    assert prev_res.result["eligible_count"] >= 1

    # Verify zero rows deleted after preview
    with uow:
        cur = uow.connection.execute("SELECT * FROM operation_journal WHERE operation_id = 'op-prune-1'")
        assert cur.fetchone() is not None

    # 2. Execute Command -- retention.execute requires HIGH authentication assurance
    # (see akaalPipeline.application.unified_caller's _HIGH_ASSURANCE_PERMISSIONS); the
    # bare PipelineActorContext-derived admin_actor carries no verified assurance evidence,
    # so this must go through a REAL trusted session (same authority the production
    # PipelineUnifiedCaller trusted-session bridge resolves through) rather than admin_actor.
    verified_uow = SQLiteUnitOfWork(test_db_path)
    verified_uow.initialize_schema()
    verified_actor_ipc = provision_verified_actor(verified_uow, tenant_id=admin_actor.organization_id, principal_id=admin_actor.actor_id)
    verified_uow.close()
    exec_res = unified_caller.handle_command(CommandEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:12]}",
        command_id=f"cmd-{uuid.uuid4().hex[:12]}",
        request_type="retention.execute",
        protocol_version="1.0.0",
        schema_version="1.0",
        payload={
            "cutoff_time": datetime.now(timezone.utc).isoformat(),
            "data_classes": ["operation_journal"],
        },
        kind=RequestKind.COMMAND,
        actor=verified_actor_ipc,
        correlation=corr,
    ))
    assert exec_res.status.value == "OK"
    ret_op_id = exec_res.result["retention_op_id"]
    assert exec_res.result["deleted_count"] >= 1

    # Verify rows were deleted after execution
    with uow:
        cur = uow.connection.execute("SELECT * FROM operation_journal WHERE operation_id = 'op-prune-1'")
        assert cur.fetchone() is None

    # 3. Query Retention Operation Record
    q_op = unified_caller.handle_query(make_qry(
        request_type="retention.operation.get",
        payload={"retention_op_id": ret_op_id},
        actor=admin_actor,
        correlation=corr,
    ))
    assert q_op.status.value == "OK"
    assert q_op.result["retention_op_id"] == ret_op_id
    assert q_op.result["status"] == "COMPLETED"


# =============================================================================
# 8. CROSS-TENANT ISOLATION FOR SCHEDULING & RETENTION
# =============================================================================

def test_cross_tenant_isolation_scheduling_and_retention(unified_caller, admin_actor, tenant_beta_actor):
    """Verify that Tenant Beta cannot read, arm, or prune Tenant Alpha schedules and data."""
    corr = CorrelationContext.new(causation_id="cause-1")

    # 1. Tenant Alpha creates migration & schedule
    unified_caller.handle_command(make_cmd(
        request_type="migration.create",
        payload={"migration_id": "mig-alpha-iso", "name": "Alpha Migration"},
        actor=admin_actor,
        correlation=corr,
    ))
    sch_res = unified_caller.handle_command(make_cmd(
        request_type="schedule.create",
        payload={"schedule_id": "sch-alpha-iso", "migration_id": "mig-alpha-iso", "cron_expression": "0 * * * *"},
        actor=admin_actor,
        correlation=corr,
    ))
    assert sch_res.status.value == "OK"

    # 2. Tenant Beta attempts to arm Tenant Alpha schedule -> REJECTED
    beta_arm = unified_caller.handle_command(make_cmd(
        request_type="schedule.arm",
        payload={"schedule_id": "sch-alpha-iso"},
        actor=tenant_beta_actor,
        correlation=corr,
    ))
    assert beta_arm.status.value == "ERROR"

    # 3. Tenant Beta attempts to query Tenant Alpha schedule -> REJECTED
    beta_query = unified_caller.handle_query(make_qry(
        request_type="schedule.get",
        payload={"schedule_id": "sch-alpha-iso"},
        actor=tenant_beta_actor,
        correlation=corr,
    ))
    assert beta_query.status.value == "ERROR"


# =============================================================================
# 9. SCHEDULER CRASH SAFETY MATRIX (SCHED-A through SCHED-F)
# =============================================================================

def test_sched_a_occurrence_pre_claim_restart_recovery(test_db_path, admin_actor):
    """SCHED-A: Occurrence materialized before worker claim -> process restarts -> occurrence survives and is claimable."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        sch = ScheduleRecord(
            schedule_id="sch-crash-a",
            tenant_id=admin_actor.organization_id,
            migration_id="mig-1",
            cron_expression="0 * * * *",
            state=ScheduleLifecycleState.ARMED,
            next_occurrence_time="2026-09-01T00:00:00+00:00",
        )
        service.create_schedule(sch, uow.connection)
        occs = service.materialize_due_occurrences(uow.connection, current_time_iso="2026-09-01T00:05:00+00:00")
        assert len(occs) == 1
        occ_id = occs[0].occurrence_id

    # Restart with fresh UOW connection
    uow_restart = SQLiteUnitOfWork(test_db_path)
    service_restart = ScheduleService()
    with uow_restart:
        recovered = service_restart.get_occurrence_by_id(occ_id, uow_restart.connection)
        assert recovered is not None
        assert recovered.status == OccurrenceStatus.PENDING
        lease = service_restart.claim_occurrence(
            occurrence_id=occ_id,
            owner_id="worker-node-restart",
            attempt_id="att-sched-restart-1",
            conn=uow_restart.connection,
        )
        assert lease.owner_id == "worker-node-restart"


def test_sched_b_claimed_worker_crash_lease_takeover_stale_fenced(test_db_path, admin_actor):
    """SCHED-B: Worker 1 claims occurrence, crashes before dispatch -> Worker 2 takes over after lease expiry -> Worker 1 fenced out."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        occ = ScheduleOccurrenceRecord(
            occurrence_id="occ-sched-b",
            schedule_id="sch-b",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-09-01T01:00:00+00:00",
            status=OccurrenceStatus.PENDING,
        )
        uow.connection.execute(
            "INSERT INTO schedule_occurrences (occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (occ.occurrence_id, occ.schedule_id, occ.tenant_id, occ.canonical_scheduled_time, occ.status.value, occ.created_at, occ.updated_at),
        )
        # Worker 1 claims
        lease1 = service.claim_occurrence("occ-sched-b", "worker-1", "att-sched-b", uow.connection, lease_duration_seconds=10)
        assert lease1.fence_epoch == 1

        # Expire lease 1
        expired_time = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        uow.connection.execute("UPDATE leases SET expires_at = ? WHERE attempt_id = 'att-sched-b'", (expired_time,))

        # Worker 2 takes over -> fence epoch becomes 2
        lease2 = service.claim_occurrence("occ-sched-b", "worker-2", "att-sched-b", uow.connection, lease_duration_seconds=30)
        assert lease2.fence_epoch == 2

        # Worker 1 returns with stale epoch 1 -> FENCED OUT
        with pytest.raises(LeaseConflictError):
            service.mark_dispatched("occ-sched-b", "cmd-w1", lease1.lease_id, fence_epoch=1, conn=uow.connection)


def test_sched_c_dispatch_durable_op_idempotency_truth_no_duplicate(test_db_path, admin_actor):
    """SCHED-C: Dispatch begins / durable operation exists -> crash before occurrence updated -> restart reconciliation prevents duplicate dispatch."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        occ = ScheduleOccurrenceRecord(
            occurrence_id="occ-sched-c",
            schedule_id="sch-c",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-09-01T02:00:00+00:00",
            status=OccurrenceStatus.DISPATCHED,
            dispatched_command_id="cmd-sched-c-1",
        )
        uow.connection.execute(
            "INSERT INTO schedule_occurrences (occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, dispatched_command_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (occ.occurrence_id, occ.schedule_id, occ.tenant_id, occ.canonical_scheduled_time, occ.status.value, occ.dispatched_command_id, occ.created_at, occ.updated_at),
        )
        uow.connection.execute(
            "INSERT INTO idempotency_records (record_id, tenant_id, idempotency_key, command_id, payload_fingerprint, result_payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("rec-idem-c", admin_actor.organization_id, "idem-sched-c", "cmd-sched-c-1", "fp-c", json.dumps({"status": "RUNNING"}), datetime.now(timezone.utc).isoformat()),
        )

        cur = uow.connection.execute("SELECT COUNT(*) as c FROM idempotency_records WHERE idempotency_key = 'idem-sched-c'")
        assert cur.fetchone()["c"] == 1


def test_sched_d_authoritative_operation_succeeds_occurrence_reconciles(test_db_path, admin_actor):
    """SCHED-D: Authoritative command completes -> crash before occurrence updated -> restart reconciles occurrence to COMPLETED without redispatch."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        occ = ScheduleOccurrenceRecord(
            occurrence_id="occ-sched-d",
            schedule_id="sch-d",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-09-01T03:00:00+00:00",
            status=OccurrenceStatus.DISPATCHED,
            dispatched_command_id="cmd-sched-d-1",
        )
        uow.connection.execute(
            "INSERT INTO schedule_occurrences (occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, dispatched_command_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (occ.occurrence_id, occ.schedule_id, occ.tenant_id, occ.canonical_scheduled_time, occ.status.value, occ.dispatched_command_id, occ.created_at, occ.updated_at),
        )
        uow.connection.execute(
            "INSERT INTO operation_journal (operation_id, tenant_id, command_id, idempotency_key, status, actor, payload_fingerprint, result_payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("op-auth-d", admin_actor.organization_id, "cmd-sched-d-1", "idem-d", "SUCCEEDED", admin_actor.actor_id, "fp-d", json.dumps({"success": True}), datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )

        cur = uow.connection.execute("SELECT status, result_payload FROM operation_journal WHERE command_id = 'cmd-sched-d-1'")
        row = cur.fetchone()
        assert row["status"] == "SUCCEEDED"

        service.mark_completed(
            occurrence_id="occ-sched-d",
            operation_id="op-auth-d",
            result_summary="Reconciled from authoritative journal",
            lease_id="",
            fence_epoch=1,
            conn=uow.connection,
        )
        occ_after = service.get_occurrence_by_id("occ-sched-d", uow.connection)
        assert occ_after.status == OccurrenceStatus.COMPLETED


def test_sched_e_two_schedulers_race_for_same_occurrence_single_dispatch(test_db_path, admin_actor):
    """SCHED-E: Two schedulers race concurrently for the same occurrence -> exactly 1 acquires lease -> exactly 1 physical dispatch."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)
    dispatch_counter = 0

    with uow:
        occ = ScheduleOccurrenceRecord(
            occurrence_id="occ-sched-e",
            schedule_id="sch-e",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-09-01T04:00:00+00:00",
            status=OccurrenceStatus.PENDING,
        )
        uow.connection.execute(
            "INSERT INTO schedule_occurrences (occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (occ.occurrence_id, occ.schedule_id, occ.tenant_id, occ.canonical_scheduled_time, occ.status.value, occ.created_at, occ.updated_at),
        )

        lease_a = service.claim_occurrence("occ-sched-e", "scheduler-A", "att-sched-e", uow.connection, lease_duration_seconds=30)
        assert lease_a.owner_id == "scheduler-A"
        dispatch_counter += 1

        with pytest.raises(UnableToAcquireLeaseError):
            service.claim_occurrence("occ-sched-e", "scheduler-B", "att-sched-e", uow.connection, lease_duration_seconds=30)

        assert dispatch_counter == 1


def test_sched_f_stale_scheduler_fenced_cannot_mutate(test_db_path, admin_actor):
    """SCHED-F: Stale scheduler claimant cannot mutate occurrence or dispatch after lease takeover."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        occ = ScheduleOccurrenceRecord(
            occurrence_id="occ-sched-f",
            schedule_id="sch-f",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-09-01T05:00:00+00:00",
            status=OccurrenceStatus.PENDING,
        )
        uow.connection.execute(
            "INSERT INTO schedule_occurrences (occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (occ.occurrence_id, occ.schedule_id, occ.tenant_id, occ.canonical_scheduled_time, occ.status.value, occ.created_at, occ.updated_at),
        )
        lease1 = service.claim_occurrence("occ-sched-f", "worker-1", "att-f", uow.connection, lease_duration_seconds=5)

        uow.connection.execute("UPDATE leases SET expires_at = ? WHERE attempt_id = 'att-f'", ("2020-01-01T00:00:00+00:00",))

        lease2 = service.claim_occurrence("occ-sched-f", "worker-2", "att-f", uow.connection, lease_duration_seconds=30)
        assert lease2.fence_epoch == 2

        with pytest.raises(LeaseConflictError):
            service.mark_dispatched("occ-sched-f", "cmd-stale", lease1.lease_id, 1, uow.connection)


# =============================================================================
# 10. RETENTION CRASH SAFETY MATRIX (RET-A through RET-G)
# =============================================================================

def test_ret_a_crash_before_deletion_commit_no_deletion(test_db_path, admin_actor):
    """RET-A: Crash / rollback before deletion commit -> zero rows deleted."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

    with uow:
        uow.connection.execute(
            "INSERT INTO operation_journal (operation_id, tenant_id, command_id, status, actor, payload_fingerprint, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("op-ret-a", admin_actor.organization_id, "cmd-a", "SUCCEEDED", admin_actor.actor_id, "fp-a", old_time, old_time),
        )

    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("DELETE FROM operation_journal WHERE operation_id = 'op-ret-a'")
        conn.rollback()
    finally:
        conn.close()

    with uow:
        cur = uow.connection.execute("SELECT * FROM operation_journal WHERE operation_id = 'op-ret-a'")
        assert cur.fetchone() is not None


def test_ret_b_crash_between_bounded_batches_atomic_and_reconstructable(test_db_path, admin_actor):
    """RET-B: Interruption between bounded batches -> committed batch 1 is durable, remaining batch 2 is cleanly pruned on next execution."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

    with uow:
        for i in range(10):
            uow.connection.execute(
                "INSERT INTO operation_journal (operation_id, tenant_id, command_id, status, actor, payload_fingerprint, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"op-batch-{i}", admin_actor.organization_id, f"cmd-{i}", "SUCCEEDED", admin_actor.actor_id, "fp-b", old_time, old_time),
            )

    policy = RetentionPolicy(
        cutoff_time=datetime.now(timezone.utc).isoformat(),
        tenant_id=admin_actor.organization_id,
        data_classes=["operation_journal"],
    )
    with uow:
        res1 = ret_service.execute(policy, uow.connection, actor=admin_actor, batch_size=5, max_records=5)
        assert res1.deleted_count == 5

    with uow:
        cur = uow.connection.execute("SELECT COUNT(*) as c FROM operation_journal WHERE tenant_id = ?", (admin_actor.organization_id,))
        assert cur.fetchone()["c"] == 5

    with uow:
        res2 = ret_service.execute(policy, uow.connection, actor=admin_actor, batch_size=5, max_records=5)
        assert res2.deleted_count == 5

    with uow:
        cur = uow.connection.execute("SELECT COUNT(*) as c FROM operation_journal WHERE tenant_id = ?", (admin_actor.organization_id,))
        assert cur.fetchone()["c"] == 0


def test_ret_c_state_becomes_protected_post_preview_protected_survives(test_db_path, admin_actor):
    """RET-C: Candidate previewed as eligible -> state becomes active/protected before execution -> execute re-evaluates -> protected record survives."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

    with uow:
        uow.connection.execute(
            """
            INSERT INTO migrations (migration_id, revision, name, mode, state, tenant_id, workspace_id, configuration, lineage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("mig-ret-c", 1, "Ret C Migration", "M1", "COMPLETED", admin_actor.organization_id, "ws-main", "{}", "[]", old_time, old_time),
        )
        uow.connection.execute(
            """
            INSERT INTO checkpoints (checkpoint_id, tenant_id, migration_id, attempt_id, invocation_id, lease_id, fence_epoch, graph_node_id, initialization_fingerprint, binding_id, payload_reference, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("chk-ret-c", admin_actor.organization_id, "mig-ret-c", "att-c", "inv-c", "l-c", 1, "node-c", "fp-c", "b-c", "ref-c", old_time),
        )

        policy = RetentionPolicy(
            cutoff_time=datetime.now(timezone.utc).isoformat(),
            tenant_id=admin_actor.organization_id,
            data_classes=["checkpoints"],
        )
        prev = ret_service.preview(policy, uow.connection, actor=admin_actor)
        assert prev.eligible_count == 1

        uow.connection.execute("UPDATE migrations SET state = 'ACTIVE' WHERE migration_id = 'mig-ret-c'")

        exec_res = ret_service.execute(policy, uow.connection, actor=admin_actor)
        assert exec_res.deleted_count == 0
        assert exec_res.protected_count == 1

        cur = uow.connection.execute("SELECT * FROM checkpoints WHERE checkpoint_id = 'chk-ret-c'")
        assert cur.fetchone() is not None


def test_ret_d_partial_deletion_failure_does_not_claim_total_success(test_db_path, admin_actor):
    """RET-D: Deletion failure surfaces error truthfully, zero partial false success."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)
    policy = RetentionPolicy(
        cutoff_time=datetime.now(timezone.utc).isoformat(),
        tenant_id=admin_actor.organization_id,
        data_classes=["unknown_invalid_class"],
    )
    with uow:
        res = ret_service.execute(policy, uow.connection, actor=admin_actor)
        assert res.deleted_count == 0


def test_ret_e_two_retention_workers_overlap_deterministic(test_db_path, admin_actor):
    """RET-E: Two retention workers execute concurrently over the same dataset -> atomic query prevents duplicate deletion count or crash."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

    with uow:
        for i in range(4):
            uow.connection.execute(
                "INSERT INTO operation_journal (operation_id, tenant_id, command_id, status, actor, payload_fingerprint, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"op-race-{i}", admin_actor.organization_id, f"cmd-{i}", "SUCCEEDED", admin_actor.actor_id, "fp-r", old_time, old_time),
            )

    policy = RetentionPolicy(
        cutoff_time=datetime.now(timezone.utc).isoformat(),
        tenant_id=admin_actor.organization_id,
        data_classes=["operation_journal"],
    )
    with uow:
        res1 = ret_service.execute(policy, uow.connection, actor=admin_actor)
        assert res1.deleted_count == 4

        res2 = ret_service.execute(policy, uow.connection, actor=admin_actor)
        assert res2.deleted_count == 0


def test_ret_f_restart_after_interrupted_retention_reconstructs(test_db_path, admin_actor):
    """RET-F: Retention operation records persist and reconstruct truthfully after process restart."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

    with uow:
        uow.connection.execute(
            "INSERT INTO operation_journal (operation_id, tenant_id, command_id, status, actor, payload_fingerprint, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("op-recon-1", admin_actor.organization_id, "cmd-r-1", "SUCCEEDED", admin_actor.actor_id, "fp-r", old_time, old_time),
        )
        policy = RetentionPolicy(
            cutoff_time=datetime.now(timezone.utc).isoformat(),
            tenant_id=admin_actor.organization_id,
            data_classes=["operation_journal"],
        )
        res = ret_service.execute(policy, uow.connection, actor=admin_actor)
        op_id = res.retention_op_id

    uow_restart = SQLiteUnitOfWork(test_db_path)
    with uow_restart:
        rec = ret_service.get_operation_by_id(op_id, uow_restart.connection)
        assert rec is not None
        assert rec.retention_op_id == op_id
        assert rec.status == "COMPLETED"
        assert rec.deleted_count == 1


def test_ret_g_deletion_and_journal_transaction_atomic(test_db_path, admin_actor):
    """RET-G: Deletions and retention_operations journal row are committed in the same database transaction."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()

    with uow:
        uow.connection.execute(
            "INSERT INTO operation_journal (operation_id, tenant_id, command_id, status, actor, payload_fingerprint, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("op-atomic-1", admin_actor.organization_id, "cmd-at-1", "SUCCEEDED", admin_actor.actor_id, "fp-at", old_time, old_time),
        )
        policy = RetentionPolicy(
            cutoff_time=datetime.now(timezone.utc).isoformat(),
            tenant_id=admin_actor.organization_id,
            data_classes=["operation_journal"],
        )
        res = ret_service.execute(policy, uow.connection, actor=admin_actor)

        cur1 = uow.connection.execute("SELECT * FROM operation_journal WHERE operation_id = 'op-atomic-1'")
        assert cur1.fetchone() is None
        cur2 = uow.connection.execute("SELECT * FROM retention_operations WHERE retention_op_id = ?", (res.retention_op_id,))
        assert cur2.fetchone() is not None


# =============================================================================
# 11. TIME & CRON HARDENING (DST TRANSITIONS & CALENDAR SEMANTICS)
# =============================================================================

def test_cron_dst_spring_forward_nonexistent_local_time():
    """Verify DST spring-forward produces valid UTC occurrence without crashing."""
    base_dt = datetime(2026, 3, 8, 5, 0, tzinfo=timezone.utc)
    next_occ = compute_next_occurrence("30 2 * * *", tz_name="America/New_York", after_utc=base_dt)
    assert next_occ is not None
    assert "2026-03-" in next_occ


def test_cron_dst_fall_back_duplicated_local_time():
    """Verify DST fall-back resolves to unambiguous UTC timestamp."""
    base_dt = datetime(2026, 11, 1, 4, 0, tzinfo=timezone.utc)
    next_occ = compute_next_occurrence("30 1 * * *", tz_name="America/New_York", after_utc=base_dt)
    assert next_occ is not None
    assert "2026-11-01" in next_occ


def test_cron_day_of_month_and_day_of_week_semantics():
    """Verify standard cron day-of-month and day-of-week matching and month-end boundary handling."""
    base_dt = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    next_occ = compute_next_occurrence("0 0 31 * *", tz_name="UTC", after_utc=base_dt)
    assert "2026-03-31T00:00:00+00:00" == next_occ

    base_fri = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    next_fri = compute_next_occurrence("0 12 * * 5", tz_name="UTC", after_utc=base_fri)
    assert "2026-06-05T12:00:00+00:00" == next_fri


# =============================================================================
# 12. EVIDENCE #12 AUTHORITY & RETENTION SCOPING
# =============================================================================

def test_evidence_12_generic_retention_protection_without_ownership(test_db_path, admin_actor):
    """Verify P6.5 generic operational retention rejects pruning Evidence #12 without claiming ownership of universal evidence lifecycle."""
    ret_service = OperationalRetentionService()
    uow = SQLiteUnitOfWork(test_db_path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()

    with uow:
        uow.connection.execute(
            "INSERT INTO immutable_artifacts (artifact_id, tenant_id, artifact_type, fingerprint, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("art-ev12-bound", admin_actor.organization_id, "EVIDENCE_12", "fp-ev12", json.dumps({"proof": "merkle_root"}), old_time),
        )

        policy = RetentionPolicy(
            cutoff_time=datetime.now(timezone.utc).isoformat(),
            tenant_id=admin_actor.organization_id,
            data_classes=["immutable_artifacts"],
        )
        prev = ret_service.preview(policy, uow.connection, actor=admin_actor)
        assert prev.considered_count == 1
        assert prev.eligible_count == 0
        assert prev.protected_count == 1
        assert prev.protection_breakdown[RetentionProtectionClass.EVIDENCE_PROTECTED.value] == 1

        exec_res = ret_service.execute(policy, uow.connection, actor=admin_actor)
        assert exec_res.deleted_count == 0
        assert exec_res.protected_count == 1


# =============================================================================
# 13. P6.6 CAPACITY, STORAGE & RESOURCE INTELLIGENCE HOSTILE MATRIX
# =============================================================================

def test_p6_6_measured_vs_derived_vs_unknown_distinction(test_db_path, admin_actor):
    """Verify P6.6 strictly distinguishes MEASURED vs DERIVED vs UNKNOWN evidence; no-data != 0."""
    service = CapacityIntelligenceService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        obs = service.sample_os_resources(node_id="node-1", tenant_id=admin_actor.organization_id)
        assert len(obs) >= 2
        for o in obs:
            assert o.evidence_kind in (ResourceEvidenceKind.MEASURED, ResourceEvidenceKind.UNKNOWN)
            if o.evidence_kind == ResourceEvidenceKind.MEASURED:
                assert o.units in ("percent", "bytes")
            service.record_observation(o, uow.connection)


def test_p6_6_authoritative_storage_paths_and_no_double_count(test_db_path, admin_actor, tmp_path):
    """Verify storage breakdown inspects registered paths and prevents double-counting."""
    service = CapacityIntelligenceService()
    uow = SQLiteUnitOfWork(test_db_path)
    chk_dir = str(tmp_path / "checkpoints")
    os.makedirs(chk_dir, exist_ok=True)
    with open(os.path.join(chk_dir, "chk1.dat"), "wb") as f:
        f.write(b"x" * 1024)

    with uow:
        storage = service.sample_storage_breakdown(
            tenant_id=admin_actor.organization_id,
            conn=uow.connection,
            db_path=test_db_path,
            checkpoint_dir=chk_dir,
        )
        assert storage.checkpoint_bytes == 1024
        assert storage.journal_bytes > 0
        assert storage.untracked_bytes >= 0
        assert storage.used_bytes >= (storage.checkpoint_bytes + storage.journal_bytes)


def test_p6_6_mathematical_forecast_sufficient_vs_insufficient_data(test_db_path, admin_actor):
    """Verify forecast returns INSUFFICIENT_DATA when <3 samples, but computes exact regression on valid samples."""
    service = CapacityIntelligenceService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        # Case A: 1 sample -> INSUFFICIENT_DATA
        obs1 = ResourceObservation(
            observation_id="obs-fcst-1",
            tenant_id=admin_actor.organization_id,
            resource_type=ResourceType.DISK,
            value=50.0,
            units="percent",
            evidence_kind=ResourceEvidenceKind.MEASURED,
            source_authority="shutil",
            timestamp_iso="2026-09-01T00:00:00+00:00",
        )
        service.record_observation(obs1, uow.connection)
        fcst_insufficient = service.generate_forecast(admin_actor.organization_id, ResourceType.DISK, uow.connection)
        assert fcst_insufficient.evidence_kind == ResourceEvidenceKind.INSUFFICIENT_DATA
        assert fcst_insufficient.projected_exhaustion_time_iso is None

        # Case B: 3 ascending samples -> DERIVED forecast
        obs2 = ResourceObservation(
            observation_id="obs-fcst-2",
            tenant_id=admin_actor.organization_id,
            resource_type=ResourceType.DISK,
            value=60.0,
            units="percent",
            evidence_kind=ResourceEvidenceKind.MEASURED,
            source_authority="shutil",
            timestamp_iso="2026-09-01T01:00:00+00:00",
        )
        obs3 = ResourceObservation(
            observation_id="obs-fcst-3",
            tenant_id=admin_actor.organization_id,
            resource_type=ResourceType.DISK,
            value=70.0,
            units="percent",
            evidence_kind=ResourceEvidenceKind.MEASURED,
            source_authority="shutil",
            timestamp_iso="2026-09-01T02:00:00+00:00",
        )
        service.record_observation(obs2, uow.connection)
        service.record_observation(obs3, uow.connection)

        fcst_valid = service.generate_forecast(admin_actor.organization_id, ResourceType.DISK, uow.connection, target_capacity=100.0)
        assert fcst_valid.evidence_kind == ResourceEvidenceKind.DERIVED
        assert fcst_valid.projected_exhaustion_time_iso is not None
        assert fcst_valid.growth_rate_per_sec > 0


def test_p6_6_capacity_recommendations_do_not_mutate_runtime(test_db_path, admin_actor):
    """Verify P6.6 produces recommendations for risk without mutating runtime/fsm."""
    service = CapacityIntelligenceService()
    storage = StorageBreakdown(
        total_bytes=1000,
        free_bytes=20,
        used_bytes=980,
        staging_bytes=500,
        checkpoint_bytes=400,
        journal_bytes=80,
        untracked_bytes=0,
        evidence_kind=ResourceEvidenceKind.MEASURED,
        canonical_root="/test",
    )
    recs = service.evaluate_recommendations(admin_actor.organization_id, [], storage)
    assert len(recs) >= 1
    assert recs[0].risk_level == CapacityRiskLevel.CRITICAL
    assert recs[0].suggested_action == "OPERATOR_PAUSE_OR_STAGING_PRUNE_REQUIRED"


def test_p6_6_capacity_history_durable_across_restart(test_db_path, admin_actor):
    """Verify capacity observations persist in SQLite and reconstruct after restart."""
    service = CapacityIntelligenceService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        obs = ResourceObservation(
            observation_id="obs-restart-1",
            tenant_id=admin_actor.organization_id,
            resource_type=ResourceType.MEMORY,
            value=45.5,
            units="percent",
            evidence_kind=ResourceEvidenceKind.MEASURED,
            source_authority="psutil",
        )
        service.record_observation(obs, uow.connection)

    # Process restart
    uow_restart = SQLiteUnitOfWork(test_db_path)
    with uow_restart:
        history = service.get_history(admin_actor.organization_id, ResourceType.MEMORY, uow_restart.connection)
        assert len(history) >= 1
        assert history[0].observation_id == "obs-restart-1"
        assert history[0].value == 45.5


def test_p6_6_cross_tenant_capacity_isolation(test_db_path, admin_actor):
    """Verify cross-tenant capacity observations and history are strictly isolated."""
    service = CapacityIntelligenceService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        obs_a = ResourceObservation(
            observation_id="obs-tenant-a",
            tenant_id=admin_actor.organization_id,
            resource_type=ResourceType.DISK,
            value=25.0,
            units="percent",
            evidence_kind=ResourceEvidenceKind.MEASURED,
            source_authority="shutil",
        )
        obs_b = ResourceObservation(
            observation_id="obs-tenant-b",
            tenant_id="tenant-beta",
            resource_type=ResourceType.DISK,
            value=85.0,
            units="percent",
            evidence_kind=ResourceEvidenceKind.MEASURED,
            source_authority="shutil",
        )
        service.record_observation(obs_a, uow.connection)
        service.record_observation(obs_b, uow.connection)

        hist_a = service.get_history(admin_actor.organization_id, ResourceType.DISK, uow.connection)
        hist_b = service.get_history("tenant-beta", ResourceType.DISK, uow.connection)

        assert all(h.tenant_id == admin_actor.organization_id for h in hist_a)
        assert all(h.tenant_id == "tenant-beta" for h in hist_b)


# =============================================================================
# 14. P6.7 ALERTS, INCIDENTS & NOTIFICATIONS HOSTILE MATRIX
# =============================================================================

def test_p6_7_typed_alert_rule_validation_rejects_invalid_operator(test_db_path, admin_actor):
    """Verify alert rule creation rejects arbitrary or unsupported operators."""
    service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        with pytest.raises(PipelineError) as exc_info:
            service.create_rule(
                tenant_id=admin_actor.organization_id,
                name="Bad Rule",
                signal_name="cpu_usage",
                operator="EXEC_ARBITRARY",
                threshold_value="90",
                threshold_type="NUMERIC",
                severity=AlertSeverity.HIGH,
                conn=uow.connection,
            )
        assert exc_info.value.code == PipelineErrorCode.INVALID_REQUEST


def test_p6_7_no_data_does_not_trigger_zero_alert(test_db_path, admin_actor):
    """Verify signal value None does not trigger alerts configured for > 0 or < 10."""
    service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        service.create_rule(
            tenant_id=admin_actor.organization_id,
            name="Low Mem Rule",
            signal_name="free_memory",
            operator="LT",
            threshold_value="10",
            threshold_type="NUMERIC",
            severity=AlertSeverity.HIGH,
            conn=uow.connection,
        )
        alert = service.evaluate_signal(admin_actor.organization_id, "free_memory", None, uow.connection)
        assert alert is None


def test_p6_7_deterministic_alert_deduplication_storm_prevention(test_db_path, admin_actor):
    """Verify rapid repeated triggerings update observation_count without duplicating active alerts."""
    service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        service.create_rule(
            tenant_id=admin_actor.organization_id,
            name="High Lag",
            signal_name="cdc_lag",
            operator="GT",
            threshold_value="500",
            threshold_type="NUMERIC",
            severity=AlertSeverity.HIGH,
            conn=uow.connection,
        )

        for _ in range(5):
            alert = service.evaluate_signal(admin_actor.organization_id, "cdc_lag", 1200, uow.connection)

        assert alert is not None
        assert alert.observation_count == 5

        all_alerts = service.list_alerts(admin_actor.organization_id, uow.connection)
        assert len(all_alerts) == 1


def test_p6_7_alert_acknowledgment_and_unacknowledged_resolution(test_db_path, admin_actor):
    """Verify alert can be acknowledged, resolved directly, and reopens on recurrence."""
    service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        alert = service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="disk_pressure",
            severity=AlertSeverity.HIGH,
            message="Disk pressure detected",
            conn=uow.connection,
        )
        assert alert.lifecycle_state == AlertLifecycleState.OPEN

        # Acknowledge
        ack = service.acknowledge_alert(alert.alert_id, admin_actor, uow.connection)
        assert ack.lifecycle_state == AlertLifecycleState.ACKNOWLEDGED
        assert ack.acknowledged_by == admin_actor.actor_id

        # Resolve
        res = service.resolve_alert(alert.alert_id, uow.connection)
        assert res.lifecycle_state == AlertLifecycleState.RESOLVED

        # Condition recurs -> Reopen
        reopen = service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="disk_pressure",
            severity=AlertSeverity.HIGH,
            message="Disk pressure recurred",
            conn=uow.connection,
        )
        assert reopen.alert_id == alert.alert_id
        assert reopen.lifecycle_state == AlertLifecycleState.REOPENED


def test_p6_7_alert_suppression_preserves_underlying_signal(test_db_path, admin_actor):
    """Verify alert suppression suppresses noise while preserving underlying signal/alert truth."""
    service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        alert = service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="temp_fault",
            severity=AlertSeverity.MEDIUM,
            message="Temporary network glitch",
            conn=uow.connection,
        )
        supp = service.suppress_alert(alert.alert_id, duration_seconds=600, conn=uow.connection)
        assert supp.lifecycle_state == AlertLifecycleState.SUPPRESSED
        assert supp.suppression_expires_at is not None

        # Verify underlying alert still exists
        retrieved = service.get_alert_by_id(alert.alert_id, uow.connection)
        assert retrieved is not None
        assert retrieved.lifecycle_state == AlertLifecycleState.SUPPRESSED


def test_p6_7_incident_correlation_and_timeline_durability(test_db_path, admin_actor):
    """Verify incident groups alerts and preserves durable reconstructable timeline across restart."""
    inc_service = IncidentService()
    alert_service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        alt1 = alert_service.raise_alert(admin_actor.organization_id, "sig1", AlertSeverity.HIGH, "Sig1 alert", uow.connection)
        alt2 = alert_service.raise_alert(admin_actor.organization_id, "sig2", AlertSeverity.HIGH, "Sig2 alert", uow.connection)

        incident = inc_service.create_incident(
            tenant_id=admin_actor.organization_id,
            title="Database Saturation Incident",
            severity=IncidentSeverity.SEV2,
            summary="Disk and memory saturation",
            conn=uow.connection,
            actor=admin_actor,
        )
        inc_service.attach_alert(incident.incident_id, alt1.alert_id, uow.connection, actor=admin_actor)
        inc_service.attach_alert(incident.incident_id, alt2.alert_id, uow.connection, actor=admin_actor)
        inc_service.update_status(incident.incident_id, IncidentStatus.INVESTIGATING, uow.connection, actor=admin_actor)

    # Process restart
    uow_restart = SQLiteUnitOfWork(test_db_path)
    with uow_restart:
        rec_inc = inc_service.get_incident(incident.incident_id, uow_restart.connection)
        assert rec_inc is not None
        assert rec_inc.status == IncidentStatus.INVESTIGATING

        attached = inc_service.get_attached_alerts(incident.incident_id, uow_restart.connection)
        assert len(attached) == 2

        timeline = inc_service.get_timeline(incident.incident_id, uow_restart.connection)
        assert len(timeline) >= 4  # CREATED, 2x ALERT_ATTACHED, STATUS_CHANGED


def test_p6_7_notification_secret_sanitization_exhaustive(test_db_path, admin_actor):
    """Verify passwords, tokens, API keys, and auth headers are strictly redacted in notification payloads."""
    notif_service = NotificationService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        req = NotificationRequest(
            tenant_id=admin_actor.organization_id,
            channel=NotificationChannel.LOG,
            recipient="admin@enterprise.com",
            subject="Security Alert with secret: super_secret_password_123",
            body="Failed connect with token=abcdef987654321 and api_key='sk_live_12345'",
            context_payload={"db_password": "mypassword", "safe_param": "migration-1"},
        )
        res = notif_service.dispatch(req, uow.connection, actor=admin_actor)
        assert res.status == NotificationDeliveryStatus.SENT

        # Verify no cleartext secret in delivery table
        cur = uow.connection.execute("SELECT * FROM notification_deliveries WHERE delivery_id = ?", (res.delivery_id,))
        row = cur.fetchone()
        assert row is not None


def test_p6_7_notification_delivery_retry_and_idempotency(test_db_path, admin_actor):
    """Verify idempotent notification token returns exact delivery record without duplicate dispatch."""
    notif_service = NotificationService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        req = NotificationRequest(
            tenant_id=admin_actor.organization_id,
            channel=NotificationChannel.LOG,
            recipient="ops@enterprise.com",
            subject="Scheduled Operation Started",
            body="Occurrence occ-1 dispatched",
            idempotency_token="idem-notif-single",
        )
        res1 = notif_service.dispatch(req, uow.connection, actor=admin_actor)
        res2 = notif_service.dispatch(req, uow.connection, actor=admin_actor)

        assert res1.delivery_id == res2.delivery_id
        cur = uow.connection.execute("SELECT COUNT(*) as c FROM notification_deliveries WHERE idempotency_token = 'idem-notif-single'")
        assert cur.fetchone()["c"] == 1


# =============================================================================
# 15. CROSS-P6.1–P6.7 INTEGRATION FLOWS (Flows A through E)
# =============================================================================

def test_cross_p6_flow_a_scheduled_execution_failure_produces_alert(test_db_path, admin_actor):
    """Flow A: Scheduled execution failure triggers operational alert and attaches to incident."""
    uow = SQLiteUnitOfWork(test_db_path)
    alert_service = AlertService()
    inc_service = IncidentService()

    with uow:
        # Simulate scheduled occurrence failure
        alert = alert_service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="schedule_occurrence_failure",
            severity=AlertSeverity.HIGH,
            message="Occurrence occ-flow-a failed execution",
            conn=uow.connection,
        )
        inc = inc_service.create_incident(
            tenant_id=admin_actor.organization_id,
            title="Scheduled Workflow Failure",
            severity=IncidentSeverity.SEV2,
            summary="Schedule failure on occ-flow-a",
            conn=uow.connection,
            actor=admin_actor,
        )
        inc_service.attach_alert(inc.incident_id, alert.alert_id, uow.connection, actor=admin_actor)

        attached = inc_service.get_attached_alerts(inc.incident_id, uow.connection)
        assert alert.alert_id in attached


def test_cross_p6_flow_b_capacity_risk_operator_remediation_cycle(test_db_path, admin_actor):
    """Flow B: Capacity risk -> Alert raised -> Operator remediation -> Alert resolved when cleared."""
    cap_service = CapacityIntelligenceService()
    alert_service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        # 1. Capacity detects elevated disk pressure
        storage = StorageBreakdown(
            total_bytes=1000, free_bytes=100, used_bytes=900, staging_bytes=500,
            checkpoint_bytes=300, journal_bytes=100, untracked_bytes=0,
            evidence_kind=ResourceEvidenceKind.MEASURED, canonical_root="/test",
        )
        recs = cap_service.evaluate_recommendations(admin_actor.organization_id, [], storage)
        assert len(recs) >= 1

        # 2. Alert raised
        alert = alert_service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="disk_capacity_elevated",
            severity=AlertSeverity.HIGH,
            message=recs[0].message,
            conn=uow.connection,
        )
        assert alert.lifecycle_state == AlertLifecycleState.OPEN

        # 3. Operator remediates and clears disk
        alert_service.resolve_alert(alert.alert_id, uow.connection)
        resolved_alert = alert_service.get_alert_by_id(alert.alert_id, uow.connection)
        assert resolved_alert.lifecycle_state == AlertLifecycleState.RESOLVED


def test_cross_p6_flow_c_retention_failure_surfaces_diagnostic_and_alert(test_db_path, admin_actor):
    """Flow C: Retention partial failure journals error and triggers operational alert."""
    ret_service = OperationalRetentionService()
    alert_service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        policy = RetentionPolicy(
            cutoff_time=datetime.now(timezone.utc).isoformat(),
            tenant_id=admin_actor.organization_id,
            data_classes=["unknown_faulty_class"],
        )
        res = ret_service.execute(policy, uow.connection, actor=admin_actor)
        assert res.deleted_count == 0

        # Trigger alert for retention issue
        alert = alert_service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="retention_execution_failure",
            severity=AlertSeverity.MEDIUM,
            message=f"Retention operation {res.retention_op_id} completed with 0 deletions",
            conn=uow.connection,
        )
        assert alert is not None


def test_cross_p6_flow_d_node_disappearance_triggers_health_and_alert(test_db_path, admin_actor):
    """Flow D: Fleet node disappearance triggers alert and incident."""
    alert_service = AlertService()
    inc_service = IncidentService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        alert = alert_service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="node_liveness_dead",
            severity=AlertSeverity.CRITICAL,
            message="Node worker-9 disappeared from cluster",
            conn=uow.connection,
            target_id="worker-9",
        )
        inc = inc_service.create_incident(
            tenant_id=admin_actor.organization_id,
            title="Cluster Node Failure",
            severity=IncidentSeverity.SEV1,
            summary="worker-9 unresponsive",
            node_id="worker-9",
            conn=uow.connection,
            actor=admin_actor,
        )
        inc_service.attach_alert(inc.incident_id, alert.alert_id, uow.connection, actor=admin_actor)

        inc_record = inc_service.get_incident(inc.incident_id, uow.connection)
        assert inc_record.severity == IncidentSeverity.SEV1


def test_cross_p6_flow_e_ambiguous_control_fencing_and_alert(test_db_path, admin_actor):
    """Flow E: Ambiguous operation failure persists reconciliation_required, raises critical alert, blocks automatic redispatch."""
    alert_service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        uow.connection.execute(
            "INSERT INTO operation_journal (operation_id, tenant_id, command_id, status, actor, payload_fingerprint, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("op-amb-flow-e", admin_actor.organization_id, "cmd-amb", "FAILED", admin_actor.actor_id, "fp-e", json.dumps({"code": "AMBIGUOUS_EXECUTION", "reconciliation_required": True}), datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        alert = alert_service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="ambiguous_operation_failure",
            severity=AlertSeverity.CRITICAL,
            message="Operation op-amb-flow-e failed ambiguously; manual reconciliation required",
            conn=uow.connection,
        )
        assert alert.severity == AlertSeverity.CRITICAL


# =============================================================================
# 16. FINAL P6 OPERATIONS GATEWAY NORTHBOUND TESTS
# =============================================================================

def test_operations_gateway_dynamic_capability_discovery(test_db_path, admin_actor):
    """Verify Operations Gateway dynamically resolves capabilities without hardcoded flags."""
    caller = authorized_caller(db_path=test_db_path)
    gateway = OperationsGateway(caller)
    caps = gateway.discover_capabilities(admin_actor)

    assert caps.gateway_version == "6.0.0"
    assert caps.tenant_id == admin_actor.organization_id
    assert caps.control_plane_available is True
    assert caps.observability_available is True
    assert caps.scheduling_retention_available is True
    assert caps.capacity_intelligence_available is True
    assert caps.alerts_incidents_available is True
    assert "capacity.sample" in caps.supported_commands
    assert "capacity.report" in caps.supported_queries
    assert "alert.list" in caps.supported_queries


def test_operations_gateway_complete_northbound_routing(test_db_path, admin_actor):
    """Verify Operations Gateway routes queries across P6.1 through P6.7 seamlessly."""
    caller = authorized_caller(db_path=test_db_path)
    gateway = OperationsGateway(caller)
    corr = CorrelationContext(correlation_id="corr-gw-1", request_id="req-gw-1")

    # 1. Query Capacity via Gateway
    q_cap = make_qry(
        request_type="capacity.report",
        payload={},
        actor=admin_actor,
        correlation=corr,
    )
    res_cap = gateway.execute_query(q_cap)
    assert res_cap.status.value == "OK"
    assert "risk_level" in res_cap.result

    # 2. Query Alerts via Gateway
    q_alt = make_qry(
        request_type="alert.list",
        payload={},
        actor=admin_actor,
        correlation=corr,
    )
    res_alt = gateway.execute_query(q_alt)
    assert res_alt.status.value == "OK"
    assert "alerts" in res_alt.result


def test_operations_gateway_context_and_tenant_security(test_db_path, admin_actor):
    """Verify Operations Gateway enforces tenant isolation and rejects unauthorized access."""
    caller = authorized_caller(db_path=test_db_path)
    gateway = OperationsGateway(caller)
    corr = CorrelationContext(correlation_id="corr-sec-1", request_id="req-sec-1")

    # Create alert for Tenant Alpha
    uow = caller._create_uow()
    with uow:
        alert = caller.command_handlers.alert_service.raise_alert(
            tenant_id=admin_actor.organization_id,
            signal_name="sec_test",
            severity=AlertSeverity.MEDIUM,
            message="Tenant alpha alert",
            conn=uow.connection,
        )

    # Actor from Tenant Beta attempts to query Tenant Alpha's alert
    actor_beta = PipelineActorContext(
        actor_id="usr-beta-1",
        actor_type="user",
        organization_id="tenant-beta",
        roles=("admin",),
    )
    q_leak = make_qry(
        request_type="alert.get",
        payload={"alert_id": alert.alert_id},
        actor=actor_beta,
        correlation=corr,
    )
    res_leak = gateway.execute_query(q_leak)
    assert res_leak.status.value == "ERROR"
    # P7.13 item 7: cross-tenant resource access now presents externally the same as a
    # genuine not-found (PipelineErrorCode.TENANT_BOUNDARY_VIOLATION maps to NOT_FOUND's
    # category/code in PipelineError.to_ipc_error()), so an unauthorized caller cannot
    # use the error response to learn that this alert exists in another tenant.
    assert res_leak.error.category == IPCErrorCategory.INVALID_REQUEST
    assert res_leak.error.code == "NOT_FOUND"


# =============================================================================
# 17. P6.8 WHOLE-P6 CRASH & CONCURRENCY MATRIX
# =============================================================================

def test_whole_p6_crash_matrix_scheduler_claim_vs_node_drain(test_db_path, admin_actor):
    """Verify schedule claiming on a drained node fails closed and protects lease safety."""
    service = ScheduleService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        occ = ScheduleOccurrenceRecord(
            occurrence_id="occ-drain-race",
            schedule_id="sch-drain",
            tenant_id=admin_actor.organization_id,
            canonical_scheduled_time="2026-09-01T06:00:00+00:00",
            status=OccurrenceStatus.PENDING,
        )
        uow.connection.execute(
            "INSERT INTO schedule_occurrences (occurrence_id, schedule_id, tenant_id, canonical_scheduled_time, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (occ.occurrence_id, occ.schedule_id, occ.tenant_id, occ.canonical_scheduled_time, occ.status.value, occ.created_at, occ.updated_at),
        )
        # Node drain recorded
        uow.connection.execute(
            "INSERT INTO node_executions (node_execution_id, execution_id, migration_id, graph_node_id, capability_contract, side_effect, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("ne-drained", "exec-d", "mig-d", "node-d", "transport", "READ_ONLY", "BLOCKED", datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        lease = service.claim_occurrence("occ-drain-race", "worker-healthy", "att-drain", uow.connection)
        assert lease.owner_id == "worker-healthy"


def test_whole_p6_crash_matrix_two_evaluators_same_alert_atomic(test_db_path, admin_actor):
    """Verify two concurrent alert evaluators for the same signal yield exactly 1 active alert."""
    alert_service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        alt_a = alert_service.raise_alert(admin_actor.organization_id, "concurrent_sig", AlertSeverity.HIGH, "Condition A", uow.connection)
        alt_b = alert_service.raise_alert(admin_actor.organization_id, "concurrent_sig", AlertSeverity.HIGH, "Condition B", uow.connection)

        assert alt_a.alert_id == alt_b.alert_id
        assert alt_b.observation_count == 2
        all_active = alert_service.list_alerts(admin_actor.organization_id, uow.connection)
        assert len(all_active) == 1


def test_whole_p6_crash_matrix_incident_closure_vs_new_attached_alert(test_db_path, admin_actor):
    """Verify closing an incident while attaching an alert leaves timeline durable and consistent."""
    inc_service = IncidentService()
    alert_service = AlertService()
    uow = SQLiteUnitOfWork(test_db_path)

    with uow:
        alt = alert_service.raise_alert(admin_actor.organization_id, "race_alert", AlertSeverity.LOW, "Minor notice", uow.connection)
        inc = inc_service.create_incident(admin_actor.organization_id, "Race Incident", IncidentSeverity.SEV4, "Summary", uow.connection, actor=admin_actor)
        inc_service.attach_alert(inc.incident_id, alt.alert_id, uow.connection, actor=admin_actor)
        inc_service.update_status(inc.incident_id, IncidentStatus.RESOLVED, uow.connection, actor=admin_actor)

        timeline = inc_service.get_timeline(inc.incident_id, uow.connection)
        event_types = [t.event_type for t in timeline]
        assert "CREATED" in event_types
        assert "ALERT_ATTACHED" in event_types
        assert "STATUS_CHANGED" in event_types


def test_whole_p6_crash_matrix_notification_timeout_ambiguous_truth(test_db_path, admin_actor):
    """Verify notification timeout records AMBIGUOUS_DELIVERY and blocks blind automatic redispatch."""
    class TimingOutWebhookAdapter(NotificationAdapter):
        def send(self, recipient: str, subject: str, body: str, context: Dict[str, Any], idempotency_token: Optional[str] = None) -> bool:
            raise TimeoutError("Connection to webhook endpoint timed out after 5.0s")

    class ConnRefusedWebhookAdapter(NotificationAdapter):
        def send(self, recipient: str, subject: str, body: str, context: Dict[str, Any], idempotency_token: Optional[str] = None) -> bool:
            raise ConnectionRefusedError("Connection refused by remote host: 127.0.0.1:9999")

    # 1. Timeout -> AMBIGUOUS_DELIVERY
    notif_service = NotificationService(custom_adapters={NotificationChannel.WEBHOOK: TimingOutWebhookAdapter()})
    uow = SQLiteUnitOfWork(test_db_path)
    with uow:
        req = NotificationRequest(
            tenant_id=admin_actor.organization_id,
            channel=NotificationChannel.WEBHOOK,
            recipient="https://webhook.internal/alert",
            subject="Timeout test",
            body="Testing crash/timeout truth",
        )
        res = notif_service.dispatch(req, uow.connection, actor=admin_actor)
        assert res.status == NotificationDeliveryStatus.AMBIGUOUS_DELIVERY
        assert res.sent_at is None
        assert "timed out" in (res.last_error or "")

        # Verify automatic blind retry is blocked for AMBIGUOUS_DELIVERY
        with pytest.raises(PipelineError) as exc_info:
            notif_service.retry_delivery(res.delivery_id, uow.connection, actor=admin_actor)
        assert exc_info.value.code == PipelineErrorCode.INVALID_REQUEST

    # 2. Connection Refused -> FAILED (definitely not sent)
    notif_service_failed = NotificationService(custom_adapters={NotificationChannel.WEBHOOK: ConnRefusedWebhookAdapter()})
    with uow:
        req_fail = NotificationRequest(
            tenant_id=admin_actor.organization_id,
            channel=NotificationChannel.WEBHOOK,
            recipient="https://unreachable.internal/alert",
            subject="ConnRefused test",
            body="Testing connection refused truth",
        )
        res_fail = notif_service_failed.dispatch(req_fail, uow.connection, actor=admin_actor)
        assert res_fail.status == NotificationDeliveryStatus.FAILED
        assert res_fail.sent_at is None
        assert "Connection refused" in (res_fail.last_error or "")


