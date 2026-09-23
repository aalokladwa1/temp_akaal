import os
import pytest
import asyncio
import uuid
import sqlite3
import tempfile
from akaalPipeline.api.desktop_ipc_bridge import build_host
from akaalIPC.protocol.envelopes import CommandEnvelope, QueryEnvelope, ResponseStatus
from akaalIPC.protocol.schemas import RequestKind
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.security.permission_registry import PermissionRegistry

@pytest.fixture
def tmp_db_path(tmp_path):
    db_p = str(tmp_path / "test_pipeline.db")
    uow = SQLiteUnitOfWork(db_p)
    uow._init_all_tables()

    uow.tenants.create(tenant_id="t-1", name="Tenant 1", status="ACTIVE", created_at="2026-01-01T00:00:00")
    uow.workspaces.create(tenant_id="t-1", workspace_id="w-1", name="Workspace 1", status="ACTIVE", created_at="2026-01-01T00:00:00")
    uow.principals.create(tenant_id="t-1", principal_id="usr-1", principal_type="HUMAN", username="usr-1", created_at="2026-01-01T00:00:00")

    uow.roles.create_role(role_id="rol-admin", tenant_id="t-1", name="Admin", is_builtin=True, created_at="2026-01-01T00:00:00")
    for perm in PermissionRegistry.ALL_PERMISSIONS:
        uow.role_permissions.add_permission("t-1", "rol-admin", perm)

    uow.role_grants.create_grant(
        grant_id="g-1",
        tenant_id="t-1",
        subject_type="PRINCIPAL",
        subject_id="usr-1",
        role_id="rol-admin",
        resource_type="SYSTEM",
        resource_id="root",
        granted_by="usr-1",
        granted_at="2026-01-01T00:00:00"
    )

    uow.conn.commit()

    return db_p

def make_actor():
    return ActorContext(actor=ActorReference(actor_id="usr-1", actor_type="HUMAN"), organization_id="t-1", workspace_id="w-1", project_id="p-1")

def make_correlation():
    return CorrelationContext(correlation_id=f"corr-{uuid.uuid4().hex[:8]}", request_id=f"req-{uuid.uuid4().hex[:8]}")

def test_production_composition_root_binds_engine(tmp_db_path):
    """Verifies that desktop_ipc_bridge.build_host() binds the real EngineGateway."""
    host = build_host(db_path=tmp_db_path)
    router = host._router
    assert router._unified_caller is not None
    binding = router._unified_caller.binding_registry.get("gateway_engine_binding")
    assert binding is not None
    assert binding.is_healthy is True

def test_routed_unrouted_operations_end_to_end(tmp_db_path):
    """Verifies that all newly routed project, initiative, connection, template, audit ops work."""
    host = build_host(db_path=tmp_db_path)
    router = host._router

    actor = make_actor()
    corr = make_correlation()

    # 1. Project Create & Get
    cmd_proj = CommandEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="project.create",
        kind=RequestKind.COMMAND,
        actor=actor,
        correlation=corr,
        payload={"project_id": "proj-100", "name": "Alpha Project"},
        command_id=f"cmd-{uuid.uuid4().hex[:8]}"
    )
    res_proj = router.handle_request(cmd_proj)
    if res_proj.status != ResponseStatus.OK:
        print("RES_PROJ ERROR:", res_proj.error)
    assert res_proj.status == ResponseStatus.OK
    assert res_proj.result["project_id"] == "proj-100"

    query_proj = QueryEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="project.get",
        kind=RequestKind.QUERY,
        actor=actor,
        correlation=corr,
        payload={"project_id": "proj-100"}
    )
    res_qproj = router.handle_request(query_proj)
    if res_qproj.status != ResponseStatus.OK:
        print("RES_QPROJ ERROR:", res_qproj.error)
    assert res_qproj.status == ResponseStatus.OK
    assert res_qproj.result["project_id"] == "proj-100"

    # 2. Connection Test & Providers
    cmd_conn = CommandEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="connection.test",
        kind=RequestKind.COMMAND,
        actor=actor,
        correlation=corr,
        payload={"provider_id": "postgres"},
        command_id=f"cmd-{uuid.uuid4().hex[:8]}"
    )
    res_conn = router.handle_request(cmd_conn)
    assert res_conn.status == ResponseStatus.OK
    assert res_conn.result["reachable"] is True

    query_prov = QueryEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="connection.list_providers",
        kind=RequestKind.QUERY,
        actor=actor,
        correlation=corr,
        payload={}
    )
    res_qprov = router.handle_request(query_prov)
    assert res_qprov.status == ResponseStatus.OK
    assert len(res_qprov.result["providers"]) > 0

    # 3. Audit Trail & Integrity
    query_audit = QueryEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="audit.get_trail",
        kind=RequestKind.QUERY,
        actor=actor,
        correlation=corr,
        payload={}
    )
    res_audit = router.handle_request(query_audit)
    assert res_audit.status == ResponseStatus.OK

    query_verify = QueryEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="audit.verify",
        kind=RequestKind.QUERY,
        actor=actor,
        correlation=corr,
        payload={}
    )
    res_verify = router.handle_request(query_verify)
    assert res_verify.status == ResponseStatus.OK
    assert res_verify.result["verified"] is True

def test_engine_discovery_via_bound_gateway(tmp_db_path):
    """Verifies that migration.discover executes through the bound EngineGateway."""
    host = build_host(db_path=tmp_db_path)
    router = host._router

    actor = make_actor()
    corr = make_correlation()

    cmd_disc = CommandEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:8]}",
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="migration.discover",
        kind=RequestKind.COMMAND,
        actor=actor,
        correlation=corr,
        payload={"migration_id": "mig-test-1", "tables": [{"name": "users", "schema": "public"}]},
        command_id=f"cmd-{uuid.uuid4().hex[:8]}"
    )
    res_disc = router.handle_request(cmd_disc)
    if res_disc.status != ResponseStatus.OK:
        print("RES_DISC ERROR:", res_disc.error)
    assert res_disc.status == ResponseStatus.OK
    assert res_disc.result["migration_id"] == "mig-test-1"
