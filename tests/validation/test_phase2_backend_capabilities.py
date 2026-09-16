"""tests/validation/test_phase2_backend_capabilities.py

Comprehensive tests for Phase 2 missing backend validation capabilities:
1. Continuous Validation lifecycle & overlap protection.
2. Maintenance / Coordinated Baseline.
3. Migration Baseline & checkpoint binding.
4. External Replication Baseline & position parsing.
5. Secure Migration Metadata Importer (DMS, GoldenGate, JSON/CSV).
6. Execute on Init, Schedule Later, Recurring, Continuous timing choices.
7. Capability & Readiness resolution.
8. IPC / UnifiedCaller exposure & tenant security isolation.
"""

from datetime import datetime, timedelta, timezone
import json
import sqlite3
import pytest

from akaalIPC.protocol.envelopes import CommandEnvelope, CorrelationContext, QueryEnvelope
from akaalIPC.security.context import ActorContext, ActorReference
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    MigrationLifecycleState,
    MigrationMode,
)
from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.orchestration.importer import MigrationMetadataImporter
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.validation import (
    BaselineType,
    CoordinationCondition,
    PositionType,
    TemporalStrategy,
    ValidationBoundaryManager,
    ValidationPipelineService,
    VerificationStatus,
)


@pytest.fixture
def test_db_path(tmp_path):
    return str(tmp_path / "test_phase2_validation.db")


@pytest.fixture
def uow(test_db_path):
    uow_inst = SQLiteUnitOfWork(db_path=test_db_path)
    return uow_inst


@pytest.fixture
def actor_tenant_a():
    return PipelineActorContext(
        actor_id="usr-tenant-a",
        actor_type="human",
        organization_id="tenant-a",
        workspace_id="ws-a",
        project_id="proj-a",
        roles=("admin", "operator"),
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.HIGH,
    )


@pytest.fixture
def actor_tenant_b():
    return PipelineActorContext(
        actor_id="usr-tenant-b",
        actor_type="human",
        organization_id="tenant-b",
        workspace_id="ws-b",
        project_id="proj-b",
        roles=("admin", "operator"),
        authentication_state=AuthenticationState.AUTHENTICATED,
        authentication_assurance=AuthenticationAssurance.HIGH,
    )


from tests.pipeline.conftest import build_test_authorization_engine


@pytest.fixture
def central_authz(uow):
    return build_test_authorization_engine(uow)


@pytest.fixture
def caller(test_db_path, uow, central_authz):
    return PipelineUnifiedCaller(
        db_path=test_db_path,
        shared_uow=uow,
        central_authz=central_authz,
    )


# =====================================================================
# 1. CONTINUOUS VALIDATION TESTS
# =====================================================================

def test_continuous_validation_lifecycle(uow, actor_tenant_a):
    conn = uow.connection
    service = ValidationPipelineService()

    payload = {
        "source_id": "src-db-1",
        "target_id": "tgt-db-1",
        "temporal_strategy": "CONTINUOUS",
    }
    mission = service.create_mission(payload, actor_tenant_a, conn)
    assert mission.temporal_strategy == TemporalStrategy.CONTINUOUS
    assert mission.state.name == "DRAFT"

    initialized = service.initialize_mission(mission.mission_id, actor_tenant_a, conn)
    assert initialized.is_ready is True

    # Start mission
    started = service.control_continuous(mission.mission_id, "start", actor_tenant_a, conn)
    assert started.state.name == "RUNNING"

    # Perform evaluation
    def dummy_evaluator(m, pos):
        return {"status": "SUCCESS", "rows_mismatched": 0}

    success, eval_res, status_msg = service.continuous_service.execute_evaluation_cycle(mission.mission_id, conn, dummy_evaluator)
    assert success is True
    assert status_msg == "SUCCESS"

    # Overlap Protection (REJECT_OVERLAP when running)
    service.continuous_service._active_evaluations[mission.mission_id] = True

    success_ov, eval_res_ov, status_msg_ov = service.continuous_service.execute_evaluation_cycle(mission.mission_id, conn, dummy_evaluator)
    assert success_ov is False
    assert "SKIPPED_OVERLAP" in status_msg_ov

    # Reset evaluating flag & Pause
    service.continuous_service._active_evaluations[mission.mission_id] = False

    paused = service.control_continuous(mission.mission_id, "pause", actor_tenant_a, conn)
    assert paused.state.name == "PAUSED"

    # Resume & Cancel
    resumed = service.control_continuous(mission.mission_id, "resume", actor_tenant_a, conn)
    assert resumed.state.name == "RUNNING"

    cancelled = service.control_continuous(mission.mission_id, "cancel", actor_tenant_a, conn)
    assert cancelled.state.name == "CANCELLED"


def test_continuous_validation_recovery(uow, actor_tenant_a):
    conn = uow.connection
    service = ValidationPipelineService()

    payload = {"source_id": "src-1", "target_id": "tgt-1", "temporal_strategy": "CONTINUOUS"}
    mission = service.create_mission(payload, actor_tenant_a, conn)
    service.initialize_mission(mission.mission_id, actor_tenant_a, conn)
    service.control_continuous(mission.mission_id, "start", actor_tenant_a, conn)

    # Recover after restart
    recovered = service.continuous_service.recover_on_restart(conn)
    assert len(recovered) == 1

    rec_after = service.continuous_service.get_mission_by_id(mission.mission_id, conn)
    assert rec_after.state.name == "RUNNING"


# =====================================================================
# 2. MAINTENANCE / COORDINATED BASELINE TESTS
# =====================================================================

def test_maintenance_baseline_declared_vs_verified(uow, actor_tenant_a):
    conn = uow.connection
    service = ValidationPipelineService()
    mgr = service.boundary_manager

    m1 = service.create_mission({"mission_id": "miss-maint-1", "source_id": "s1", "target_id": "t1"}, actor_tenant_a, conn)
    m2 = service.create_mission({"mission_id": "miss-maint-2", "source_id": "s1", "target_id": "t1"}, actor_tenant_a, conn)

    # WRITES_STOPPED_DECLARED -> VerificationStatus.DECLARED
    base_decl = mgr.establish_maintenance_baseline(
        mission_id=m1.mission_id,
        condition=CoordinationCondition.WRITES_STOPPED_DECLARED,
        operator_declaration="Operator confirmed application maintenance window",
        actor=actor_tenant_a,
        conn=conn,
    )
    assert base_decl.baseline_type == BaselineType.MAINTENANCE_COORDINATED
    assert base_decl.verification_status == VerificationStatus.DECLARED
    assert base_decl.provenance_details["operator_declaration"] == "Operator confirmed application maintenance window"

    # READONLY_QUIESCENCE_VERIFIED -> VerificationStatus.VERIFIED
    base_verif = mgr.establish_maintenance_baseline(
        mission_id=m2.mission_id,
        condition=CoordinationCondition.READONLY_QUIESCENCE_VERIFIED,
        operator_declaration="Verified read-only mode via provider telemetry",
        actor=actor_tenant_a,
        conn=conn,
    )
    assert base_verif.verification_status == VerificationStatus.VERIFIED

    # Check persistence
    fetched = mgr.get_baseline(base_decl.baseline_id, conn)
    assert fetched is not None
    assert fetched.baseline_id == base_decl.baseline_id


# =====================================================================
# 3. MIGRATION BASELINE TESTS
# =====================================================================

def test_migration_baseline_binding(uow, actor_tenant_a, actor_tenant_b):
    conn = uow.connection
    service = ValidationPipelineService()
    mgr = service.boundary_manager

    # Create mission first
    miss_1 = service.create_mission({"mission_id": "miss-mig-1", "source_id": "s1", "target_id": "t1"}, actor_tenant_a, conn)
    miss_2 = service.create_mission({"mission_id": "miss-mig-2", "source_id": "s1", "target_id": "t1"}, actor_tenant_a, conn)
    miss_3 = service.create_mission({"mission_id": "miss-mig-3", "source_id": "s1", "target_id": "t1"}, actor_tenant_a, conn)

    # Create canonical migration aggregate in repository
    mig = MigrationAggregate(
        migration_id="mig-phase2-100",
        revision=1,
        name="Phase2 Test Migration",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.CONFIGURING,
        tenant_id=actor_tenant_a.organization_id,
        workspace_id=actor_tenant_a.workspace_id,
        project_id=actor_tenant_a.project_id,
    )
    uow.repository.save(mig, connection=conn)

    # Create checkpoint in DB
    chk_id = "chk-100"
    conn.execute(
        """INSERT INTO checkpoints (checkpoint_id, tenant_id, workspace_id, project_id, migration_id, execution_id, generation, attempt_id, invocation_id, lease_id, fence_epoch, graph_node_id, initialization_fingerprint, binding_id, payload_reference, created_at)
           VALUES (?, ?, ?, ?, ?, 'exec-1', 1, 'att-1', 'inv-1', 'lease-1', 1, 'node-1', 'fp-1', 'bind-1', 'payload-1', ?)""",
        (chk_id, actor_tenant_a.organization_id, actor_tenant_a.workspace_id, actor_tenant_a.project_id, mig.migration_id, datetime.now(timezone.utc).isoformat()),
    )

    # Establish migration baseline
    base = mgr.establish_migration_baseline(
        mission_id=miss_1.mission_id,
        migration_id=mig.migration_id,
        checkpoint_id=chk_id,
        actor=actor_tenant_a,
        conn=conn,
    )
    assert base.baseline_type == BaselineType.INHERITED_MIGRATION
    assert base.verification_status == VerificationStatus.VERIFIED
    assert base.migration_id == mig.migration_id
    assert base.checkpoint_id == chk_id

    # Cross-tenant attempt must fail closed
    with pytest.raises(PipelineError) as exc_info:
        mgr.establish_migration_baseline(
            mission_id=miss_2.mission_id,
            migration_id=mig.migration_id,
            checkpoint_id=chk_id,
            actor=actor_tenant_b,
            conn=conn,
        )
    assert exc_info.value.code in (PipelineErrorCode.NOT_FOUND, PipelineErrorCode.POLICY_DENIED, PipelineErrorCode.TENANT_BOUNDARY_VIOLATION)

    # Missing checkpoint must fail
    with pytest.raises(PipelineError) as exc_info:
        mgr.establish_migration_baseline(
            mission_id=miss_3.mission_id,
            migration_id=mig.migration_id,
            checkpoint_id="non-existent-chk",
            actor=actor_tenant_a,
            conn=conn,
        )
    assert exc_info.value.code == PipelineErrorCode.NOT_FOUND


# =====================================================================
# 4. EXTERNAL REPLICATION BASELINE TESTS
# =====================================================================

def test_external_replication_baseline_positions(uow, actor_tenant_a):
    conn = uow.connection
    service = ValidationPipelineService()
    mgr = service.boundary_manager

    m1 = service.create_mission({"mission_id": "miss-rep-1", "source_provider": "Oracle", "target_provider": "PostgreSQL"}, actor_tenant_a, conn)
    m2 = service.create_mission({"mission_id": "miss-rep-2", "source_provider": "PostgreSQL", "target_provider": "PostgreSQL"}, actor_tenant_a, conn)
    m3 = service.create_mission({"mission_id": "miss-rep-3", "source_provider": "MySQL", "target_provider": "PostgreSQL"}, actor_tenant_a, conn)
    m4 = service.create_mission({"mission_id": "miss-rep-4", "source_provider": "Oracle", "target_provider": "PostgreSQL"}, actor_tenant_a, conn)
    m5 = service.create_mission({"mission_id": "miss-rep-5", "source_provider": "MySQL", "target_provider": "PostgreSQL"}, actor_tenant_a, conn)

    # Oracle SCN
    base_scn = mgr.establish_external_replication_baseline(
        mission_id=m1.mission_id,
        provider="ORACLE",
        position_type=PositionType.ORACLE_SCN,
        position_value="1234567890",
        actor=actor_tenant_a,
        conn=conn,
    )
    assert base_scn.verification_status == VerificationStatus.EXTERNALLY_ASSERTED
    assert base_scn.position_value == "1234567890"

    # Postgres LSN
    base_lsn = mgr.establish_external_replication_baseline(
        mission_id=m2.mission_id,
        provider="POSTGRES",
        position_type=PositionType.POSTGRES_LSN,
        position_value="0/16B3748",
        actor=actor_tenant_a,
        conn=conn,
    )
    assert base_lsn.position_type in ("POSTGRES_LSN", "POSTGRESQL_LSN")

    # MySQL GTID
    base_gtid = mgr.establish_external_replication_baseline(
        mission_id=m3.mission_id,
        provider="MYSQL",
        position_type=PositionType.MYSQL_GTID,
        position_value="3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5",
        actor=actor_tenant_a,
        conn=conn,
    )
    assert base_gtid.position_type == "MYSQL_GTID"

    # Malformed SCN must fail
    with pytest.raises(PipelineError) as exc_info:
        mgr.establish_external_replication_baseline(
            mission_id=m4.mission_id,
            provider="ORACLE",
            position_type=PositionType.ORACLE_SCN,
            position_value="INVALID_SCN",
            actor=actor_tenant_a,
            conn=conn,
        )
    assert exc_info.value.code == PipelineErrorCode.INVALID_REQUEST

    # Provider mismatch must fail
    with pytest.raises(PipelineError) as exc_info:
        mgr.establish_external_replication_baseline(
            mission_id=m5.mission_id,
            provider="MYSQL",
            position_type=PositionType.ORACLE_SCN,
            position_value="123456",
            actor=actor_tenant_a,
            conn=conn,
        )
    # Prefixed SCN string like "SCN-1048576" must fail closed
    with pytest.raises(PipelineError) as exc_info:
        mgr.establish_external_replication_baseline(
            mission_id=m4.mission_id,
            provider="ORACLE",
            position_type=PositionType.ORACLE_SCN,
            position_value="SCN-1048576",
            actor=actor_tenant_a,
            conn=conn,
        )
    assert exc_info.value.code == PipelineErrorCode.INVALID_REQUEST
    assert "positive integer" in str(exc_info.value)


# =====================================================================
# 5. METADATA IMPORTER TESTS (AWS DMS, GOLDENGATE, DEVKROS JSON/CSV)
# =====================================================================

def test_metadata_importer_aws_dms(actor_tenant_a):
    importer = MigrationMetadataImporter()
    dms_json = json.dumps({
        "rules": [
            {
                "rule-type": "selection",
                "rule-id": "1",
                "rule-name": "1",
                "object-locator": {"schema-name": "hr", "table-name": "employees"},
                "rule-action": "include",
            },
            {
                "rule-type": "transformation",
                "rule-id": "2",
                "rule-target": "schema",
                "object-locator": {"schema-name": "hr", "table-name": "%"},
                "rule-action": "rename",
                "value": "target_hr",
            },
        ],
        "secret_password": "super_secret_password_123",
    })

    prop = importer.parse_and_create_proposal(
        content=dms_json,
        filename="dms_task_settings.json",
        tenant_id=actor_tenant_a.organization_id,
        workspace_id=actor_tenant_a.workspace_id,
        project_id=actor_tenant_a.project_id,
    )

    assert prop.format_type == "AWS_DMS"
    assert prop.is_proposal_only is True
    assert len(prop.proposed_correspondences) == 1
    corr = prop.proposed_correspondences[0]
    assert corr.source_schema == "hr"
    assert corr.source_table == "employees"
    assert corr.target_schema == "target_hr"

    # Redaction test
    assert len(prop.security_redactions) > 0
    assert any("secret_password" in r for r in prop.security_redactions)


def test_metadata_importer_goldengate_and_csv(actor_tenant_a):
    importer = MigrationMetadataImporter()

    # GoldenGate param file
    gg_content = """
    -- Oracle GoldenGate Extract Parameter File
    TABLE sales.orders;
    MAP sales.customers, TARGET db_target.customers;
    """
    prop_gg = importer.parse_and_create_proposal(
        content=gg_content,
        filename="dirprm/ext1.prm",
        tenant_id=actor_tenant_a.organization_id,
        workspace_id=actor_tenant_a.workspace_id,
    )
    assert prop_gg.format_type == "GOLDENGATE"
    assert len(prop_gg.proposed_correspondences) >= 2

    # CSV Mapping
    csv_content = """source_schema,source_table,target_schema,target_table
inventory,items,target_inv,items
inventory,stock,target_inv,stock
"""
    prop_csv = importer.parse_and_create_proposal(
        content=csv_content,
        filename="table_map.csv",
        tenant_id=actor_tenant_a.organization_id,
        workspace_id=actor_tenant_a.workspace_id,
    )
    assert prop_csv.format_type == "DEVKROS_CSV"
    assert len(prop_csv.proposed_correspondences) == 2


def test_metadata_importer_security_limits(actor_tenant_a):
    importer = MigrationMetadataImporter()

    # Oversized file > 5MB
    large_content = "x" * (5 * 1024 * 1024 + 10)
    with pytest.raises(ValueError) as exc_info:
        importer.parse_and_create_proposal(
            content=large_content,
            filename="large.json",
            tenant_id=actor_tenant_a.organization_id,
            workspace_id=actor_tenant_a.workspace_id,
        )
    assert "exceeds maximum size" in str(exc_info.value)


# =====================================================================
# 6. RUN TIMING TESTS (EXECUTE ON INIT, SCHEDULE LATER, RECURRING)
# =====================================================================

def test_execute_on_init(uow, actor_tenant_a):
    conn = uow.connection
    service = ValidationPipelineService()

    payload = {
        "source_id": "src-init",
        "target_id": "tgt-init",
        "temporal_strategy": "EXECUTE_ON_INIT",
    }
    mission = service.create_mission(payload, actor_tenant_a, conn)
    assert mission.state.name == "DRAFT"

    # Execute on init runs initialize -> execute
    res = service.execute_mission(mission.mission_id, actor_tenant_a, conn)
    assert res["status"] in ("SUCCESS", "COMPLETED")

    updated = service.get_mission(mission.mission_id, actor_tenant_a, conn)
    assert updated.state.name in ("COMPLETED", "SUCCESS")
    assert updated.evaluation_count == 1


def test_schedule_later_and_recurring(uow, actor_tenant_a):
    conn = uow.connection
    service = ValidationPipelineService()

    future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    # Schedule Later
    payload_sched = {
        "source_id": "src-sched",
        "target_id": "tgt-sched",
        "temporal_strategy": "SCHEDULE_LATER",
        "schedule_time": future_time,
    }
    mission_sched = service.create_mission(payload_sched, actor_tenant_a, conn)
    assert mission_sched.schedule_id is not None

    # Recurring
    payload_rec = {
        "source_id": "src-rec",
        "target_id": "tgt-rec",
        "temporal_strategy": "RECURRING",
        "cron_expression": "0 * * * *",
    }
    mission_rec = service.create_mission(payload_rec, actor_tenant_a, conn)
    assert mission_rec.schedule_id is not None
    assert mission_rec.temporal_strategy == TemporalStrategy.RECURRING


# =====================================================================
# 7. IPC & UNIFIED CALLER DISPATCH & TENANT ISOLATION TESTS
# =====================================================================

def test_ipc_command_and_query_dispatch(caller, uow, actor_tenant_a, actor_tenant_b):
    # 1. Create Mission via IPC Command
    actor_ctx_a = ActorContext(
        actor=ActorReference(actor_id="usr-tenant-a", actor_type="human"),
        organization_id="tenant-a",
        provenance="external",
    )

    from akaalIPC.protocol.schemas import RequestKind

    cmd_create = CommandEnvelope(
        request_id="req-cmd-1",
        protocol_version="1.0",
        schema_version="1.0",
        request_type="validation.create_mission",
        kind=RequestKind.COMMAND,
        command_id="cmd-1",
        actor=actor_ctx_a,
        correlation=CorrelationContext(correlation_id="corr-1", request_id="req-cmd-1"),
        payload={"source_id": "src-ipc", "target_id": "tgt-ipc", "temporal_strategy": "EXECUTE_ON_INIT"},
    )

    res_cmd = caller.handle_command(cmd_create)
    assert res_cmd.status.name == "OK"
    mission_id = res_cmd.result["mission_id"]

    # 2. Get Mission via IPC Query
    query_get = QueryEnvelope(
        request_id="req-qry-1",
        protocol_version="1.0",
        schema_version="1.0",
        request_type="validation.get_mission",
        kind=RequestKind.QUERY,
        actor=actor_ctx_a,
        correlation=CorrelationContext(correlation_id="corr-2", request_id="req-qry-1"),
        payload={"mission_id": mission_id},
    )

    res_qry = caller.handle_query(query_get)
    assert res_qry.status.name == "OK"
    assert res_qry.result["mission_id"] == mission_id

    # 3. Cross-Tenant IPC Query attempt from Tenant B must fail closed
    actor_ctx_b = ActorContext(
        actor=ActorReference(actor_id="usr-tenant-b", actor_type="human"),
        organization_id="tenant-b",
        provenance="external",
    )

    query_cross = QueryEnvelope(
        request_id="req-qry-cross",
        protocol_version="1.0",
        schema_version="1.0",
        request_type="validation.get_mission",
        kind=RequestKind.QUERY,
        actor=actor_ctx_b,
        correlation=CorrelationContext(correlation_id="corr-cross", request_id="req-qry-cross"),
        payload={"mission_id": mission_id},
    )

    res_cross = caller.handle_query(query_cross)
    assert res_cross.status.name == "ERROR"
