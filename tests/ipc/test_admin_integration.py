import os
import tempfile
import sys
from types import ModuleType

if "typer" not in sys.modules:
    dummy_typer = ModuleType("typer")
    dummy_typer.Typer = lambda **kwargs: dummy_typer
    dummy_typer.command = lambda *args, **kwargs: (lambda f: f)
    dummy_typer.callback = lambda *args, **kwargs: (lambda f: f)
    dummy_typer.Option = lambda default=None, *a, **kw: default
    dummy_typer.Argument = lambda default=None, *a, **kw: default
    sys.modules["typer"] = dummy_typer
import pytest
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from akaalIPC.protocol.errors import IPCErrorCategory
from tests.pipeline.conftest import authorized_caller, make_query, make_command


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
def admin_actor():
    return ActorContext(
        actor=ActorReference(actor_id="user-admin-01", actor_type="user", display_name="Primary Admin"),
        organization_id="org-enterprise-root",
        workspace_id="ws-enterprise-main",
        project_id="proj-default",
        environment="production",
        roles=("admin", "owner"),
        scopes=("admin.read", "admin.write"),
    )


@pytest.fixture
def adversarial_actor():
    return ActorContext(
        actor=ActorReference(actor_id="unauth-attacker-01", actor_type="user", display_name="Hostile Attacker"),
        organization_id="org-rogue",
        workspace_id="ws-rogue",
        project_id="proj-rogue",
        environment="production",
        roles=("guest",),
        scopes=(),
    )


def test_admin_queries_smoke(temp_db_path, admin_actor):
    """Test all 29 administrative queries through the canonical PipelineUnifiedCaller."""
    caller = authorized_caller(db_path=temp_db_path)
    try:
        queries = [
            ("admin.enterprise.hierarchy", {}),
            ("admin.organization.list", {}),
            ("admin.workspace.list", {"org_id": "org-enterprise-root"}),
            ("admin.environment.list", {}),
            ("admin.cost_center.list", {}),
            ("admin.user.list", {}),
            ("admin.team.list", {}),
            ("admin.contractor.list", {}),
            ("admin.service_account.list", {}),
            ("admin.governance.summary", {}),
            ("admin.governance.exceptions", {}),
            ("admin.governance.gates", {}),
            ("admin.role.list", {}),
            ("admin.directory.sync_status", {}),
            ("admin.template.list", {}),
            ("admin.profile.list", {}),
            ("admin.connector.list", {}),
            ("admin.plugin.list", {}),
            ("admin.infra.agents", {}),
            ("admin.infra.endpoints", {}),
            ("admin.compliance.frameworks", {}),
            ("admin.compliance.evidence_retention", {}),
            ("admin.audit.ledger", {"limit": 10, "offset": 0}),
            ("admin.audit.sessions", {}),
            ("admin.platform.license", {}),
            ("admin.platform.health", {}),
            ("admin.integration.siem", {}),
            ("admin.integration.webhooks", {}),
            ("admin.integration.keys", {}),
        ]

        assert len(queries) == 29

        for q_type, payload in queries:
            q = make_query(q_type, payload, admin_actor, CorrelationContext.new())
            res = caller.handle_query(q)
            assert res.status == CallerResultStatus.OK, f"Query {q_type} failed with status {res.status}: {res.error}"
            assert res.result is not None, f"Query {q_type} returned None result"

    finally:
        caller.close()


def test_admin_commands_authorized_execution(temp_db_path, admin_actor):
    """Test representative administrative commands with an authorized actor."""
    caller = authorized_caller(db_path=temp_db_path)
    try:
        commands = [
            ("admin.organization.create", {"organization_id": "org-new-01", "name": "New Organization Inc", "tier": "ENTERPRISE"}),
            ("admin.organization.update", {"organization_id": "org-new-01", "name": "Updated Org Inc"}),
            ("admin.workspace.create", {"workspace_id": "ws-new-01", "org_id": "org-new-01", "name": "Main Dev Workspace"}),
            ("admin.workspace.update", {"workspace_id": "ws-new-01", "name": "Updated Workspace Name"}),
            ("admin.user.create", {"user_id": "usr-alice-01", "email": "alice@org-new.com", "name": "Alice Smith"}),
            ("admin.role.create", {"role_id": "role-custom-auditor", "name": "Custom Auditor", "permissions": ["audit.read"]}),
            ("admin.role.assign", {"user_id": "usr-alice-01", "role_id": "role-custom-auditor"}),
            ("admin.governance.request_exception", {"policy_id": "pol-01", "reason": "Emergency maintenance window"}),
            ("admin.key.rotate", {"key_id": "key-master-01"}),
            ("admin.connector.create", {"connector_id": "conn-custom-db", "name": "Custom DB Driver", "type": "JDBC"}),
            ("admin.plugin.install", {"plugin_id": "plg-custom-validator"}),
        ]

        for cmd_type, payload in commands:
            cmd = make_command(cmd_type, payload, admin_actor, CorrelationContext.new())
            res = caller.handle_command(cmd)
            assert res.status == CallerResultStatus.OK, f"Command {cmd_type} failed with status {res.status}: {res.error}"
            assert res.result is not None

    finally:
        caller.close()


def test_admin_fail_closed_security_adversarial_actor(temp_db_path, adversarial_actor):
    """Verify that administrative commands FAIL CLOSED for adversarial / unauthorized actors."""
    caller = authorized_caller(db_path=temp_db_path)
    try:
        protected_commands = [
            ("admin.organization.create", {"organization_id": "org-hack-01", "name": "Hacked Org"}),
            ("admin.user.create", {"user_id": "usr-rogue", "email": "rogue@evil.com", "name": "Rogue Agent"}),
            ("admin.role.create", {"role_id": "role-evil-root", "name": "Evil Root", "permissions": ["*"]}),
            ("admin.key.rotate", {"key_id": "key-master-01"}),
            ("admin.mfa.enforce", {"user_id": "global", "mfa_policy": "FIDO2"}),
            ("admin.governance.request_exception", {"policy_id": "pol-sec", "reason": "Bypass security"}),
        ]

        for cmd_type, payload in protected_commands:
            cmd = make_command(cmd_type, payload, adversarial_actor, CorrelationContext.new())
            res = caller.handle_command(cmd)
            # Security verification: MUST fail closed with ERROR status and FORBIDDEN error category
            assert res.status == CallerResultStatus.ERROR, (
                f"Adversarial command {cmd_type} did not fail closed! Status: {res.status}, Result: {res.result}"
            )
            assert res.error is not None
            assert res.error.category == IPCErrorCategory.FORBIDDEN, (
                f"Expected FORBIDDEN error category for {cmd_type}, got {res.error.category}"
            )
            assert res.error.code == "FORBIDDEN" or "denied" in res.error.message.lower() or "forbidden" in res.error.message.lower() or "not active" in res.error.message.lower()

    finally:
        caller.close()


def test_admin_real_transport_router_roundtrip(temp_db_path, admin_actor):
    """End-to-end transport roundtrip: wire Envelope -> SchemaRegistry -> IPCRouter -> PipelineUnifiedCaller -> canonical authority."""
    from akaalIPC.application.router import IPCRouter
    from akaalIPC.protocol.schemas import SchemaRegistry, register_core_pipeline_schemas
    from akaalIPC.protocol.envelopes import ResponseStatus

    registry = SchemaRegistry()
    register_core_pipeline_schemas(registry)
    caller = authorized_caller(db_path=temp_db_path)
    router = IPCRouter(schema_registry=registry, unified_caller=caller)
    try:
        # Representative Query
        q_env = make_query("admin.organization.list", {}, admin_actor, CorrelationContext.new())
        resp = router.handle_request(q_env)
        assert resp.status == ResponseStatus.OK
        assert resp.result is not None

        # Representative Command
        c_env = make_command("admin.organization.create", {"organization_id": "org-routed-01", "name": "Routed Org"}, admin_actor, CorrelationContext.new())
        resp_cmd = router.handle_request(c_env)
        assert resp_cmd.status == ResponseStatus.OK
        assert resp_cmd.result["tenant_id"] == "org-routed-01"

        # Protected Command with adversarial actor fails closed at router boundary
        unauth_actor = ActorContext(
            actor=ActorReference(actor_id="unauth-hacker", actor_type="user"),
            organization_id="org-bad",
            roles=("guest",),
        )
        bad_cmd = make_command("admin.organization.create", {"organization_id": "org-pwned", "name": "Pwned Org"}, unauth_actor, CorrelationContext.new())
        bad_resp = router.handle_request(bad_cmd)
        assert bad_resp.status == ResponseStatus.ERROR
        assert bad_resp.error.category == IPCErrorCategory.FORBIDDEN
    finally:
        caller.close()


def test_connection_lifecycle_ipc(temp_db_path, admin_actor):
    """Verifies enterprise connection creation, lookup, update, test, and deletion through UnifiedCaller."""
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # 1. Create connection
        c_env = make_command(
            "connection.create",
            {
                "id": "conn-test-01",
                "name": "Production Postgres",
                "provider_id": "postgresql",
                "family": "RELATIONAL",
                "endpoint_display": "pg-primary.internal:5432",
            },
            admin_actor,
            CorrelationContext.new(),
        )
        res_create = caller.handle_command(c_env)
        assert res_create.status == CallerResultStatus.OK
        assert res_create.result["status"] == "CREATED"
        assert res_create.result["connection_id"] == "conn-test-01"

        # 2. Get connection
        q_get = make_query(
            "connection.get",
            {"connection_id": "conn-test-01"},
            admin_actor,
            CorrelationContext.new(),
        )
        res_get = caller.handle_query(q_get)
        assert res_get.status == CallerResultStatus.OK
        assert res_get.result["name"] == "Production Postgres"
        assert res_get.result["provider_id"] == "postgresql"

        # 3. List connections
        q_list = make_query("connection.list", {}, admin_actor, CorrelationContext.new())
        res_list = caller.handle_query(q_list)
        assert res_list.status == CallerResultStatus.OK
        assert res_list.result["total_count"] == 1
        assert res_list.result["connections"][0]["id"] == "conn-test-01"

        # 4. Test connection
        c_test = make_command(
            "connection.test",
            {"connection_id": "conn-test-01"},
            admin_actor,
            CorrelationContext.new(),
        )
        res_test = caller.handle_command(c_test)
        assert res_test.status == CallerResultStatus.OK
        assert res_test.result["connection_id"] == "conn-test-01"

        # 5. Update connection with lifecycle_state and tags
        c_upd = make_command(
            "connection.update",
            {
                "connection_id": "conn-test-01",
                "name": "Production Postgres Updated",
                "lifecycle_state": "DISABLED",
                "tags": ["Production", "CoreDB"],
            },
            admin_actor,
            CorrelationContext.new(),
        )
        res_upd = caller.handle_command(c_upd)
        assert res_upd.status == CallerResultStatus.OK
        assert res_upd.result["status"] == "UPDATED"

        # Verify get returned updated lifecycle_state and tags
        res_get2 = caller.handle_query(q_get)
        assert res_get2.status == CallerResultStatus.OK
        assert res_get2.result["name"] == "Production Postgres Updated"
        assert res_get2.result["lifecycle_state"] == "DISABLED"
        assert res_get2.result["tags"] == ["Production", "CoreDB"]

        # 6. List providers
        q_provs = make_query("connection.list_providers", {}, admin_actor, CorrelationContext.new())
        res_provs = caller.handle_query(q_provs)
        assert res_provs.status == CallerResultStatus.OK
        assert "postgresql" in res_provs.result["providers"]

        # 7. Delete connection
        c_del = make_command(
            "connection.delete",
            {"connection_id": "conn-test-01"},
            admin_actor,
            CorrelationContext.new(),
        )
        res_del = caller.handle_command(c_del)
        assert res_del.status == CallerResultStatus.OK
        assert res_del.result["status"] == "DELETED"

        # 8. Verify list is now empty
        res_list2 = caller.handle_query(q_list)
        assert res_list2.status == CallerResultStatus.OK
        assert res_list2.result["total_count"] == 0
    finally:
        caller.close()


def test_project_and_initiative_lifecycle_ipc(temp_db_path, admin_actor):
    """Verifies project & initiative creation, lookup, update, list, and deletion through UnifiedCaller."""
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # 1. Create initiative
        c_init = make_command(
            "initiative.create",
            {
                "id": "init-cloud-2026",
                "name": "Cloud Migration 2026",
                "key": "CLD26",
                "objective": "Migrate on-prem systems to modern cloud data services.",
            },
            admin_actor,
            CorrelationContext.new(),
        )
        res_init = caller.handle_command(c_init)
        assert res_init.status == CallerResultStatus.OK
        assert res_init.result["initiative_id"] == "init-cloud-2026"

        # 2. Get initiative
        q_init = make_query(
            "initiative.get",
            {"initiative_id": "init-cloud-2026"},
            admin_actor,
            CorrelationContext.new(),
        )
        res_q_init = caller.handle_query(q_init)
        assert res_q_init.status == CallerResultStatus.OK
        assert res_q_init.result["name"] == "Cloud Migration 2026"
        assert res_q_init.result["key"] == "CLD26"

        # 3. Create project linked to initiative
        c_proj = make_command(
            "project.create",
            {
                "id": "proj-core-banking",
                "name": "Core Banking Data Plane",
                "key": "BANK",
                "description": "Ledger and transactions migration project.",
                "initiative_id": "init-cloud-2026",
            },
            admin_actor,
            CorrelationContext.new(),
        )
        res_proj = caller.handle_command(c_proj)
        assert res_proj.status == CallerResultStatus.OK
        assert res_proj.result["project_id"] == "proj-core-banking"

        # 4. Get project
        q_proj = make_query(
            "project.get",
            {"project_id": "proj-core-banking"},
            admin_actor,
            CorrelationContext.new(),
        )
        res_q_proj = caller.handle_query(q_proj)
        assert res_q_proj.status == CallerResultStatus.OK
        assert res_q_proj.result["name"] == "Core Banking Data Plane"
        assert res_q_proj.result["initiative_name"] == "Cloud Migration 2026"

        # 5. List projects
        q_list_proj = make_query("project.list", {}, admin_actor, CorrelationContext.new())
        res_list_p = caller.handle_query(q_list_proj)
        assert res_list_p.status == CallerResultStatus.OK
        assert res_list_p.result["total_count"] == 1
        assert res_list_p.result["projects"][0]["id"] == "proj-core-banking"

        # 6. Update project
        c_upd_proj = make_command(
            "project.update",
            {"project_id": "proj-core-banking", "status": "ARCHIVED", "description": "Archived banking project."},
            admin_actor,
            CorrelationContext.new(),
        )
        res_upd_p = caller.handle_command(c_upd_proj)
        assert res_upd_p.status == CallerResultStatus.OK

        # 7. Delete project
        c_del_proj = make_command(
            "project.delete",
            {"project_id": "proj-core-banking"},
            admin_actor,
            CorrelationContext.new(),
        )
        res_del_p = caller.handle_command(c_del_proj)
        assert res_del_p.status == CallerResultStatus.OK
        assert res_del_p.result["status"] == "DELETED"

        # 8. Delete initiative
        c_del_init = make_command(
            "initiative.delete",
            {"initiative_id": "init-cloud-2026"},
            admin_actor,
            CorrelationContext.new(),
        )
        res_del_i = caller.handle_command(c_del_init)
        assert res_del_i.status == CallerResultStatus.OK
        assert res_del_i.result["status"] == "DELETED"

        # 9. Template delete
        c_del_tmpl = make_command(
            "template.delete",
            {"template_id": "tmpl-standard-pg"},
            admin_actor,
            CorrelationContext.new(),
        )
        res_del_t = caller.handle_command(c_del_tmpl)
        assert res_del_t.status == CallerResultStatus.OK
        assert res_del_t.result["status"] == "DELETED"
    finally:
        caller.close()


def test_connection_edge_cases_and_reference_protection(temp_db_path, admin_actor):
    """Verifies edge cases: non-existent checks, probe types, config staleness, and active migration deletion protection."""
    from akaalPipeline.contracts.errors import PipelineErrorCode
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # 1. Non-existent connection test should fail with NOT_FOUND
        c_bad_test = make_command("connection.test", {"connection_id": "non-existent-conn"}, admin_actor, CorrelationContext.new())
        res_bad_test = caller.handle_command(c_bad_test)
        assert res_bad_test.status == CallerResultStatus.ERROR
        assert res_bad_test.error.code == "NOT_FOUND"

        # 2. Non-existent connection update should fail with NOT_FOUND
        c_bad_upd = make_command("connection.update", {"connection_id": "non-existent-conn", "name": "New"}, admin_actor, CorrelationContext.new())
        res_bad_upd = caller.handle_command(c_bad_upd)
        assert res_bad_upd.status == CallerResultStatus.ERROR
        assert res_bad_upd.error.code == "NOT_FOUND"

        # 3. Non-existent connection delete should fail with NOT_FOUND
        c_bad_del = make_command("connection.delete", {"connection_id": "non-existent-conn"}, admin_actor, CorrelationContext.new())
        res_bad_del = caller.handle_command(c_bad_del)
        assert res_bad_del.status == CallerResultStatus.ERROR
        assert res_bad_del.error.code == "NOT_FOUND"

        # 4. Create connection and verify probe types
        c_create = make_command(
            "connection.create",
            {"id": "conn-active-ref-01", "name": "Prod DB", "provider_id": "postgresql", "family": "RELATIONAL", "endpoint_display": "localhost:5432"},
            admin_actor,
            CorrelationContext.new(),
        )
        assert caller.handle_command(c_create).status == CallerResultStatus.OK

        c_perm_test = make_command("connection.test", {"connection_id": "conn-active-ref-01", "probe_type": "permission"}, admin_actor, CorrelationContext.new())
        res_perm = caller.handle_command(c_perm_test)
        assert res_perm.status == CallerResultStatus.OK
        assert "permissions" in res_perm.result
        assert len(res_perm.result["permissions"]) == 3

        c_cap_test = make_command("connection.test", {"connection_id": "conn-active-ref-01", "probe_type": "capability"}, admin_actor, CorrelationContext.new())
        res_cap = caller.handle_command(c_cap_test)
        assert res_cap.status == CallerResultStatus.OK
        assert "capabilities" in res_cap.result
        assert res_cap.result["capabilities"]["cdc_supported"] is True

        # 5. Modifying configuration transitions verification_state to CONFIG_CHANGED_SINCE_TEST
        c_upd_cfg = make_command("connection.update", {"connection_id": "conn-active-ref-01", "parameters": {"port": 5433}}, admin_actor, CorrelationContext.new())
        assert caller.handle_command(c_upd_cfg).status == CallerResultStatus.OK

        q_conn = make_query("connection.get", {"connection_id": "conn-active-ref-01"}, admin_actor, CorrelationContext.new())
        res_conn = caller.handle_query(q_conn)
        assert res_conn.status == CallerResultStatus.OK
        assert res_conn.result["verification_state"] == "CONFIG_CHANGED_SINCE_TEST"

        # 6. Active migration reference protection: insert active migration referencing this connection
        uow = caller._create_uow()
        with uow:
            import json
            uow.connection.execute(
                """
                INSERT INTO migrations (
                    migration_id, revision, name, mode, state, tenant_id, workspace_id,
                    configuration, lineage, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "mig-test-active-01", 1, "Active Test Migration", "M1_BULK", "EXECUTING",
                    "default-tenant", "default-workspace",
                    json.dumps({"source_connection_id": "conn-active-ref-01"}),
                    "[]", "2026-09-23T00:00:00Z", "2026-09-23T00:00:00Z"
                )
            )

        # Deleting connection without force must fail with CONFLICT
        c_del_blocked = make_command("connection.delete", {"connection_id": "conn-active-ref-01"}, admin_actor, CorrelationContext.new())
        res_blocked = caller.handle_command(c_del_blocked)
        assert res_blocked.status == CallerResultStatus.ERROR
        assert res_blocked.error.code == "CONFLICT"

        # Forced deletion succeeds
        c_del_forced = make_command("connection.delete", {"connection_id": "conn-active-ref-01", "force": True}, admin_actor, CorrelationContext.new())
        assert caller.handle_command(c_del_forced).status == CallerResultStatus.OK

    finally:
        caller.close()


def test_project_initiative_edge_cases_and_protection(temp_db_path, admin_actor):
    """Verifies edge cases: non-existent project/initiative delete, active workload protection, and bidirectional link sync."""
    caller = authorized_caller(db_path=temp_db_path)
    try:
        # 1. Non-existent project delete fails with NOT_FOUND
        c_bad_p = make_command("project.delete", {"project_id": "non-existent-proj"}, admin_actor, CorrelationContext.new())
        res_bad_p = caller.handle_command(c_bad_p)
        assert res_bad_p.status == CallerResultStatus.ERROR
        assert res_bad_p.error.code == "NOT_FOUND"

        # 2. Non-existent initiative delete fails with NOT_FOUND
        c_bad_i = make_command("initiative.delete", {"initiative_id": "non-existent-init"}, admin_actor, CorrelationContext.new())
        res_bad_i = caller.handle_command(c_bad_i)
        assert res_bad_i.status == CallerResultStatus.ERROR
        assert res_bad_i.error.code == "NOT_FOUND"

        # 3. Create initiative and project with bidirectional sync
        c_init = make_command("initiative.create", {"id": "init-sync-01", "name": "Sync Initiative"}, admin_actor, CorrelationContext.new())
        assert caller.handle_command(c_init).status == CallerResultStatus.OK

        c_proj = make_command("project.create", {"id": "proj-sync-01", "name": "Sync Project", "initiative_id": "init-sync-01"}, admin_actor, CorrelationContext.new())
        assert caller.handle_command(c_proj).status == CallerResultStatus.OK

        # Verify initiative has proj-sync-01 in associated_project_ids
        q_init = make_query("initiative.get", {"initiative_id": "init-sync-01"}, admin_actor, CorrelationContext.new())
        res_init = caller.handle_query(q_init)
        assert "proj-sync-01" in res_init.result["associated_project_ids"]
        assert res_init.result["associated_project_count"] == 1

        # 4. Active migration reference protection on project
        uow = caller._create_uow()
        with uow:
            import json
            uow.connection.execute(
                """
                INSERT INTO migrations (
                    migration_id, revision, name, mode, state, tenant_id, workspace_id,
                    project_id, configuration, lineage, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "mig-test-active-02", 1, "Project Migration", "M1_BULK", "EXECUTING",
                    "default-tenant", "default-workspace", "proj-sync-01",
                    "{}", "[]", "2026-09-23T00:00:00Z", "2026-09-23T00:00:00Z"
                )
            )

        c_del_p_blocked = make_command("project.delete", {"project_id": "proj-sync-01"}, admin_actor, CorrelationContext.new())
        res_p_blocked = caller.handle_command(c_del_p_blocked)
        assert res_p_blocked.status == CallerResultStatus.ERROR
        assert res_p_blocked.error.code == "CONFLICT"

        # Once migration completes, project deletion succeeds and updates initiative
        with uow:
            uow.connection.execute("UPDATE migrations SET state = 'COMPLETED' WHERE migration_id = 'mig-test-active-02'")

        res_p_del = caller.handle_command(c_del_p_blocked)
        assert res_p_del.status == CallerResultStatus.OK
        assert res_p_del.result["status"] == "DELETED"

        res_init2 = caller.handle_query(q_init)
        assert "proj-sync-01" not in res_init2.result["associated_project_ids"]
        assert res_init2.result["associated_project_count"] == 0

    finally:
        caller.close()



