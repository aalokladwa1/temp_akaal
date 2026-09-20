import tempfile
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

from akaalIPC.protocol.schemas import SchemaRegistry, register_core_pipeline_schemas, RequestKind
from akaalIPC.protocol.envelopes import QueryEnvelope, CommandEnvelope
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.policy.contracts import PolicyDecision, PolicyResult, PolicySubject, PolicyAction, PolicyResource


class MockCentralAuthz:
    def authorize(self, *args, **kwargs):
        return PolicyDecision(
            decision_id="dec-test-1",
            policy_version="1.0",
            subject=PolicySubject(actor_id="user-1", actor_type="human"),
            action=PolicyAction(name="settings.update"),
            resource=PolicyResource(resource_id="settings", resource_type="domain"),
            result=PolicyResult.ALLOW,
            reason="Test Authorized",
        )


def test_settings_schemas_registered():
    registry = SchemaRegistry()
    register_core_pipeline_schemas(registry)
    for req_type, kind in [("settings.get", RequestKind.QUERY), ("settings.update", RequestKind.COMMAND), ("settings.reset", RequestKind.COMMAND)]:
        res = registry.validate(
            request_type=req_type,
            schema_version="1.0",
            kind=kind,
            payload={"domain": "runtime"},
        )
        assert res.is_valid is True, f"Schema validation failed for {req_type}: {res.error}"


def test_settings_get_execution_returns_authoritative_domains():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_settings_get.db")
        caller = PipelineUnifiedCaller(db_path=db_path, central_authz=MockCentralAuthz())

        actor = ActorContext(
            actor=ActorReference(actor_id="user-1", actor_type="human", display_name="Test Admin"),
            organization_id="org-1",
            workspace_id="ws-1",
            project_id="proj-1",
        )
        correlation = CorrelationContext.new()

        env = QueryEnvelope(
            request_id=correlation.request_id,
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="settings.get",
            kind=RequestKind.QUERY,
            actor=actor,
            correlation=correlation,
            payload={"domain": "all"},
        )

        res = caller.handle_query(env)
        assert res.status == CallerResultStatus.OK, f"Query failed with error: {res.error}"
        data = res.result
        assert "runtime" in data
        assert "connectors" in data
        assert "storage" in data
        assert "notifications" in data
        assert "integrations" in data
        assert "logging" in data
        assert "advanced" in data
        assert data["runtime"]["governedMaxWorkerLimit"] == 64


def test_settings_update_execution_applies_and_audits():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_settings_update.db")
        caller = PipelineUnifiedCaller(db_path=db_path, central_authz=MockCentralAuthz())

        actor = ActorContext(
            actor=ActorReference(actor_id="user-1", actor_type="human", display_name="Test Admin"),
            organization_id="org-1",
            workspace_id="ws-1",
            project_id="proj-1",
        )
        correlation = CorrelationContext.new()

        env = CommandEnvelope(
            request_id=correlation.request_id,
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="settings.update",
            kind=RequestKind.COMMAND,
            actor=actor,
            correlation=correlation,
            command_id="cmd-update-1",
            payload={"domain": "logging", "settings": {"engineLogLevel": "DEBUG"}},
        )

        res = caller.handle_command(env)
        assert res.status == CallerResultStatus.OK, f"Command failed with error: {res.error}"
        assert res.result["domain"] == "logging"
        assert res.result["status"] == "APPLIED"

        # Verify audit trail event recording
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM audit_trail WHERE action = 'settings.update.logging'")
        row = cur.fetchone()
        assert row is not None, "Audit event for settings.update.logging was not recorded."
        conn.close()


def test_settings_update_non_writable_domains_rejection():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_settings_non_writable.db")
        caller = PipelineUnifiedCaller(db_path=db_path, central_authz=MockCentralAuthz())

        actor = ActorContext(
            actor=ActorReference(actor_id="user-1", actor_type="human", display_name="Test Admin"),
            organization_id="org-1",
            workspace_id="ws-1",
            project_id="proj-1",
        )

        for non_writable_domain in ["connectors", "integrations", "advanced"]:
            correlation = CorrelationContext.new()
            env = CommandEnvelope(
                request_id=correlation.request_id,
                protocol_version="1.0.0",
                schema_version="1.0",
                request_type="settings.update",
                kind=RequestKind.COMMAND,
                actor=actor,
                correlation=correlation,
                command_id=f"cmd-update-{non_writable_domain}",
                payload={"domain": non_writable_domain, "settings": {"someKey": "val"}},
            )
            res = caller.handle_command(env)
            assert res.status == CallerResultStatus.ERROR
            assert "is read-only" in res.error.message


def test_settings_reset_non_writable_domains_rejection():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_settings_reset_non_writable.db")
        caller = PipelineUnifiedCaller(db_path=db_path, central_authz=MockCentralAuthz())

        actor = ActorContext(
            actor=ActorReference(actor_id="user-1", actor_type="human", display_name="Test Admin"),
            organization_id="org-1",
            workspace_id="ws-1",
            project_id="proj-1",
        )

        for non_writable_domain in ["connectors", "integrations", "advanced"]:
            correlation = CorrelationContext.new()
            env = CommandEnvelope(
                request_id=correlation.request_id,
                protocol_version="1.0.0",
                schema_version="1.0",
                request_type="settings.reset",
                kind=RequestKind.COMMAND,
                actor=actor,
                correlation=correlation,
                command_id=f"cmd-reset-{non_writable_domain}",
                payload={"domain": non_writable_domain},
            )
            res = caller.handle_command(env)
            assert res.status == CallerResultStatus.ERROR
            assert "is read-only" in res.error.message


def test_settings_update_governed_policy_rejection():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_settings_policy.db")
        caller = PipelineUnifiedCaller(db_path=db_path, central_authz=MockCentralAuthz())

        actor = ActorContext(
            actor=ActorReference(actor_id="user-1", actor_type="human", display_name="Test Admin"),
            organization_id="org-1",
            workspace_id="ws-1",
            project_id="proj-1",
        )
        correlation = CorrelationContext.new()

        # Exceeding worker cap of 64 should be rejected
        env = CommandEnvelope(
            request_id=correlation.request_id,
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="settings.update",
            kind=RequestKind.COMMAND,
            actor=actor,
            correlation=correlation,
            command_id="cmd-policy-1",
            payload={"domain": "runtime", "settings": {"preferredMaxWorkers": 128}},
        )

        res = caller.handle_command(env)
        assert res.status == CallerResultStatus.ERROR
        assert "governed maximum bound of 64" in res.error.message


def test_settings_reset_execution_restores_defaults():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_settings_reset.db")
        caller = PipelineUnifiedCaller(db_path=db_path, central_authz=MockCentralAuthz())

        actor = ActorContext(
            actor=ActorReference(actor_id="user-1", actor_type="human", display_name="Test Admin"),
            organization_id="org-1",
            workspace_id="ws-1",
            project_id="proj-1",
        )
        correlation = CorrelationContext.new()

        env = CommandEnvelope(
            request_id=correlation.request_id,
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="settings.reset",
            kind=RequestKind.COMMAND,
            actor=actor,
            correlation=correlation,
            command_id="cmd-reset-1",
            payload={"domain": "logging"},
        )

        res = caller.handle_command(env)
        assert res.status == CallerResultStatus.OK
        assert res.result["domain"] == "logging"
        assert res.result["status"] == "RESET_APPLIED"
