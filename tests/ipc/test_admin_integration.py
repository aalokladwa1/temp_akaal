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
