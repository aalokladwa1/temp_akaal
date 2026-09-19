"""tests/ipc/test_migration_blocker_closures.py

Unit and integration tests for the Migration 4-blocker closure implementation:
1. migration.discover: Removes static fallback dict, delegates to MigrationMetadataImporter / connector discovery.
2. migration.get_plan: Removes hardcoded 3-node DAG, retrieves compiled ExecutionPlan artifact from ArtifactRegistry.
3. migration.readiness: Assembles checks dynamically from readiness, policy, capacity, and governance authorities.
4. migration.checkpoint: Uses CheckpointManager and active execution fencing context.
"""

import json
import os
import sqlite3
import sys
from types import ModuleType
import pytest

if "typer" not in sys.modules:
    dummy_typer = ModuleType("typer")
    dummy_typer.Typer = lambda **kwargs: dummy_typer
    dummy_typer.command = lambda *args, **kwargs: (lambda f: f)
    dummy_typer.callback = lambda *args, **kwargs: (lambda f: f)
    dummy_typer.Option = lambda default=None, *a, **kw: default
    dummy_typer.Argument = lambda default=None, *a, **kw: default
    sys.modules["typer"] = dummy_typer

from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode
from akaalPipeline.application.command_handlers import CommandHandlerRegistry
from akaalPipeline.application.query_service import PipelineQueryService
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
from akaalPipeline.contracts.serialization import canonical_fingerprint
from akaalPipeline.operations.idempotency import IdempotencyService
from akaalPipeline.operations.leases import LeaseManager
from akaalPipeline.operations.service import OperationService
from akaalPipeline.orchestration.compiler import GraphCompiler
from akaalPipeline.recovery.checkpoints import CheckpointManager
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.artifacts import ArtifactRegistry, ImmutableArtifact
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def memory_uow():
    uow = SQLiteUnitOfWork(db_path=":memory:")
    uow.initialize_schema()
    return uow


@pytest.fixture
def actor_context():
    return PipelineActorContext(
        actor_id="usr-test-123",
        actor_type="human",
        organization_id="default-tenant",
        workspace_id="default-workspace",
        project_id="default-project",
        roles=("ADMIN",),
    )


@pytest.fixture
def command_handlers(memory_uow):
    repo = memory_uow.repository
    op_service = OperationService()
    idemp_service = IdempotencyService()
    lease_mgr = LeaseManager()
    from akaalPipeline.execution.controller import PipelineExecutionController
    from akaalPipeline.capabilities.catalog import CapabilityCatalog
    from akaalPipeline.capabilities.bindings import BindingRegistry
    from akaalPipeline.capabilities.resolver import CapabilityResolver
    
    catalog = CapabilityCatalog()
    binding_reg = BindingRegistry()
    resolver = CapabilityResolver(catalog, binding_reg)
    controller = PipelineExecutionController(resolver, binding_reg, lease_mgr, op_service)
    art_reg = ArtifactRegistry()
    chk_mgr = CheckpointManager(lease_mgr)
    
    handlers = CommandHandlerRegistry(
        repository=repo,
        operation_service=op_service,
        idempotency_service=idemp_service,
        execution_controller=controller,
        artifact_registry=art_reg,
        checkpoint_manager=chk_mgr,
    )
    return handlers, repo, art_reg, chk_mgr


@pytest.fixture
def query_service(memory_uow, command_handlers):
    _, repo, art_reg, _ = command_handlers
    op_service = OperationService()
    qs = PipelineQueryService(repository=repo, operation_service=op_service)
    qs.artifact_registry = art_reg
    return qs


def test_blocker_1_discover_metadata_delegation(command_handlers, actor_context, memory_uow):
    handlers, _, _, _ = command_handlers
    
    # Case A: When manifest content is provided, metadata_importer parses it (not hardcoded fallback)
    dms_manifest = json.dumps({
        "rules": [
            {"rule-type": "selection", "rule-id": "1", "rule-action": "include", "object-locator": {"schema-name": "hr", "table-name": "employees"}}
        ]
    })
    res_import = handlers.handle_discover_metadata(
        payload={"migration_id": "mig-disc-1", "content": dms_manifest, "filename": "dms.json"},
        actor=actor_context,
        uow=memory_uow,
    )
    assert res_import["status"] == "COMPLETED"
    assert res_import["total_tables"] == 1
    assert res_import["tables"][0]["name"] == "employees"
    assert res_import["tables"][0]["schema"] == "hr"
    
    # Case B: Executed discovery passing explicit empty tables returns COMPLETED with empty list
    res_explicit = handlers.handle_discover_metadata(
        payload={"migration_id": "mig-disc-2", "tables": []},
        actor=actor_context,
        uow=memory_uow,
    )
    assert res_explicit["status"] == "COMPLETED"
    assert res_explicit["tables"] == []
    assert res_explicit["total_tables"] == 0

    # Case C: Unexecuted / unavailable discovery without binding or manifest raises UNAAVAILABLE exception
    with pytest.raises(PipelineError) as exc_info:
        handlers.handle_discover_metadata(
            payload={"migration_id": "mig-disc-3"},
            actor=actor_context,
            uow=memory_uow,
        )
    assert exc_info.value.code == PipelineErrorCode.UNAVAILABLE


def test_blocker_2_get_plan_from_artifact_registry(query_service, command_handlers, actor_context, memory_uow):
    handlers, repo, art_reg, _ = command_handlers
    
    # 1. Create migration aggregate without plan_id
    mig_id = "mig-plan-test"
    agg = MigrationAggregate(
        migration_id=mig_id,
        revision=1,
        name="Plan Test Migration",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
    )
    repo.save(agg, connection=memory_uow.connection)

    # Missing plan_id raises INVALID_REQUEST
    with pytest.raises(PipelineError) as exc_info:
        query_service.get_plan(migration_id=mig_id, actor=actor_context, conn=memory_uow.connection)
    assert exc_info.value.code == PipelineErrorCode.INVALID_REQUEST
    
    # 2. Compile a real plan and register in ArtifactRegistry
    compiler = GraphCompiler()
    plan = compiler.compile_plan(
        plan_id=f"art-plan-{mig_id}",
        migration_id=mig_id,
        mode=MigrationMode.M1_BULK,
        configuration={"tables": ["custom_table_a", "custom_table_b"]},
    )
    art = ImmutableArtifact.create(
        artifact_id=plan.plan_id,
        artifact_type="execution_plan",
        content=plan.to_dict(),
    )
    art_reg.register(art, conn=memory_uow.connection)
    
    # Update aggregate with plan_id
    agg.plan_id = plan.plan_id
    agg.revision += 1
    repo.save(agg, connection=memory_uow.connection)
    
    # 3. Query get_plan successfully returns compiled plan
    res = query_service.get_plan(migration_id=mig_id, actor=actor_context, conn=memory_uow.connection)
    assert res["plan_id"] == plan.plan_id
    assert len(res["nodes"]) > 0
    node_ids = [n["id"] for n in res["nodes"]]
    assert "n1_extract" not in node_ids
    assert "n2_transform" not in node_ids
    assert "n3_load" not in node_ids


def test_blocker_3_get_readiness_dynamic_authority_assembly(query_service, command_handlers, actor_context, memory_uow):
    handlers, repo, art_reg, _ = command_handlers
    conn = memory_uow.connection
    
    # -------------------------------------------------------------------------
    # Test 1 — Spoofed connection evidence
    # Persist configuration containing spoofed flags with NO canonical probe evidence
    # -------------------------------------------------------------------------
    mig_spoofed_conn = "mig-spoofed-conn"
    agg_spoofed_conn = MigrationAggregate(
        migration_id=mig_spoofed_conn,
        revision=1,
        name="Spoofed Connection Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
        configuration={
            "connection_id": "conn-123",
            "connection_verified": True,
            "probe_verified": True,
            "connection_probe": {"status": "PASSED", "is_healthy": True},
        },
    )
    repo.save(agg_spoofed_conn, connection=conn)
    
    res_spoofed_conn = query_service.get_readiness(migration_id=mig_spoofed_conn, actor=actor_context, conn=conn)
    cats_spoofed_conn = {c["category"]: c["status"] for c in res_spoofed_conn["checks"]}
    assert cats_spoofed_conn["NETWORK"] == "FAILED"
    assert res_spoofed_conn["overall_status"] == "NOT_READY"

    # -------------------------------------------------------------------------
    # Test 2 — Genuine connection evidence
    # Provide valid canonical probe/connection verification evidence via database attestation table
    # -------------------------------------------------------------------------
    mig_genuine_conn = "mig-genuine-conn"
    agg_genuine_conn = MigrationAggregate(
        migration_id=mig_genuine_conn,
        revision=1,
        name="Genuine Connection Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
        configuration={"connection_id": "conn-456"},
    )
    repo.save(agg_genuine_conn, connection=conn)
    
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS connection_probe_attestations (
            attestation_id TEXT PRIMARY KEY,
            migration_id TEXT,
            connection_id TEXT,
            tenant_id TEXT,
            status TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO connection_probe_attestations VALUES ('att-1', ?, 'conn-456', ?, 'PASSED', '2026-09-18T12:00:00')",
        (mig_genuine_conn, actor_context.tenant_id),
    )

    res_genuine_conn = query_service.get_readiness(migration_id=mig_genuine_conn, actor=actor_context, conn=conn)
    cats_genuine_conn = {c["category"]: c["status"] for c in res_genuine_conn["checks"]}
    assert cats_genuine_conn["NETWORK"] == "PASSED"

    # -------------------------------------------------------------------------
    # Test 3 — Failed canonical connection evidence
    # Attestation/probe is FAILED; spoofed flags in configuration must be ignored
    # -------------------------------------------------------------------------
    mig_failed_conn = "mig-failed-conn"
    agg_failed_conn = MigrationAggregate(
        migration_id=mig_failed_conn,
        revision=1,
        name="Failed Connection Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
        configuration={"connection_verified": True, "connection_id": "conn-789"},
    )
    repo.save(agg_failed_conn, connection=conn)
    conn.execute(
        "INSERT INTO connection_probe_attestations VALUES ('att-2', ?, 'conn-789', ?, 'FAILED', '2026-09-18T12:00:00')",
        (mig_failed_conn, actor_context.tenant_id),
    )

    res_failed_conn = query_service.get_readiness(migration_id=mig_failed_conn, actor=actor_context, conn=conn)
    cats_failed_conn = {c["category"]: c["status"] for c in res_failed_conn["checks"]}
    assert cats_failed_conn["NETWORK"] == "FAILED"

    # -------------------------------------------------------------------------
    # Test 4 — Spoofed schema evidence
    # Persist schema_verified = True without canonical compatibility evidence
    # -------------------------------------------------------------------------
    mig_spoofed_schema = "mig-spoofed-schema"
    agg_spoofed_schema = MigrationAggregate(
        migration_id=mig_spoofed_schema,
        revision=1,
        name="Spoofed Schema Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
        configuration={
            "schema_verified": True,
            "schema_assessment": {"status": "PASSED", "is_compatible": True},
        },
    )
    repo.save(agg_spoofed_schema, connection=conn)

    res_spoofed_schema = query_service.get_readiness(migration_id=mig_spoofed_schema, actor=actor_context, conn=conn)
    cats_spoofed_schema = {c["category"]: c["status"] for c in res_spoofed_schema["checks"]}
    assert cats_spoofed_schema["SCHEMA"] == "FAILED"
    assert res_spoofed_schema["overall_status"] == "NOT_READY"

    # -------------------------------------------------------------------------
    # Test 5 — Genuine schema compatibility evidence
    # Real record in validation_missions table with linked_migration_id and state PASSED
    # -------------------------------------------------------------------------
    mig_genuine_schema = "mig-genuine-schema"
    agg_genuine_schema = MigrationAggregate(
        migration_id=mig_genuine_schema,
        revision=1,
        name="Genuine Schema Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
    )
    repo.save(agg_genuine_schema, connection=conn)
    conn.execute(
        """
        INSERT INTO validation_missions (mission_id, tenant_id, workspace_id, project_id, name, linked_migration_id, state, created_at, updated_at)
        VALUES ('val-m-001', ?, ?, ?, 'Val Mission', ?, 'PASSED', '2026-09-18T12:00:00', '2026-09-18T12:00:00')
        """,
        (actor_context.tenant_id, actor_context.workspace_id, actor_context.project_id, mig_genuine_schema),
    )

    res_genuine_schema = query_service.get_readiness(migration_id=mig_genuine_schema, actor=actor_context, conn=conn)
    cats_genuine_schema = {c["category"]: c["status"] for c in res_genuine_schema["checks"]}
    assert cats_genuine_schema["SCHEMA"] == "PASSED"

    # -------------------------------------------------------------------------
    # Test 6 — Failed/incomplete schema evidence
    # Canonical validation mission has state FAILED
    # -------------------------------------------------------------------------
    mig_failed_schema = "mig-failed-schema"
    agg_failed_schema = MigrationAggregate(
        migration_id=mig_failed_schema,
        revision=1,
        name="Failed Schema Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
        configuration={"schema_verified": True},
    )
    repo.save(agg_failed_schema, connection=conn)
    conn.execute(
        """
        INSERT INTO validation_missions (mission_id, tenant_id, workspace_id, project_id, name, linked_migration_id, state, created_at, updated_at)
        VALUES ('val-m-002', ?, ?, ?, 'Failed Val Mission', ?, 'FAILED', '2026-09-18T12:00:00', '2026-09-18T12:00:00')
        """,
        (actor_context.tenant_id, actor_context.workspace_id, actor_context.project_id, mig_failed_schema),
    )

    res_failed_schema = query_service.get_readiness(migration_id=mig_failed_schema, actor=actor_context, conn=conn)
    cats_failed_schema = {c["category"]: c["status"] for c in res_failed_schema["checks"]}
    assert cats_failed_schema["SCHEMA"] == "FAILED"

    # -------------------------------------------------------------------------
    # Test 7 — Cross-resource evidence
    # Evidence belonging to another migration or tenant must NOT satisfy readiness
    # -------------------------------------------------------------------------
    mig_cross_res = "mig-cross-resource"
    agg_cross_res = MigrationAggregate(
        migration_id=mig_cross_res,
        revision=1,
        name="Cross Resource Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
    )
    repo.save(agg_cross_res, connection=conn)
    conn.execute(
        """
        INSERT INTO validation_missions (mission_id, tenant_id, workspace_id, project_id, name, linked_migration_id, state, created_at, updated_at)
        VALUES ('val-m-003', 'other-tenant-id', ?, ?, 'Other Tenant Mission', ?, 'PASSED', '2026-09-18T12:00:00', '2026-09-18T12:00:00')
        """,
        (actor_context.workspace_id, actor_context.project_id, mig_cross_res),
    )

    res_cross_res = query_service.get_readiness(migration_id=mig_cross_res, actor=actor_context, conn=conn)
    cats_cross_res = {c["category"]: c["status"] for c in res_cross_res["checks"]}
    assert cats_cross_res["SCHEMA"] == "FAILED"


def test_blocker_4_checkpoint_manager_and_runtime_fencing(command_handlers, actor_context, memory_uow):
    handlers, repo, art_reg, chk_mgr = command_handlers
    
    mig_id = "mig-chk-test"
    agg = MigrationAggregate(
        migration_id=mig_id,
        revision=1,
        name="Checkpoint Test",
        mode=MigrationMode.M1_BULK,
        state=MigrationLifecycleState.DRAFT,
        tenant_id=actor_context.tenant_id,
        workspace_id=actor_context.workspace_id,
        project_id=actor_context.project_id,
    )
    repo.save(agg, connection=memory_uow.connection)
    
    res = handlers.handle_trigger_checkpoint(
        payload={"migration_id": mig_id, "checkpoint_id": "chk-001"},
        actor=actor_context,
        uow=memory_uow,
    )
    assert res["status"] == "ACCEPTED"
    assert res["checkpoint_id"] == "chk-001"
    assert "lease_id" in res
    assert "fence_epoch" in res
    
    cur = memory_uow.connection.execute("SELECT * FROM checkpoints WHERE checkpoint_id = 'chk-001'")
    row = cur.fetchone()
    assert row is not None
    assert row["checkpoint_id"] == "chk-001"
    assert row["lease_id"] == res["lease_id"]
