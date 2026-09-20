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
from akaalIPC.protocol.envelopes import QueryEnvelope
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResultStatus
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.state.repositories import SQLiteMigrationRepository
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode


def test_estate_summary_schema_registered():
    registry = SchemaRegistry()
    register_core_pipeline_schemas(registry)
    res = registry.validate(
        request_type="estate.summary",
        schema_version="1.0",
        kind=RequestKind.QUERY,
        payload={},
    )
    assert res.is_valid is True, f"Schema validation failed: {res.error}"


def test_estate_summary_execution_returns_authoritative_projection():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_pipeline.db")
        caller = PipelineUnifiedCaller(db_path=db_path)

        # Create a test migration in SQLite repo
        repo = SQLiteMigrationRepository(db_path=db_path)
        agg = MigrationAggregate(
            migration_id="mig-1",
            revision=1,
            name="Test Migration",
            mode=MigrationMode.M1_BULK,
            state=MigrationLifecycleState.ACTIVE,
            tenant_id="tenant-1",
            workspace_id="ws-1",
            project_id="proj-1",
            configuration={"source_engine": "PostgreSQL", "target_engine": "Snowflake"},
        )
        repo.save(agg)

        actor = ActorContext(
            actor=ActorReference(actor_id="user-1", actor_type="human", display_name="Test User"),
            organization_id="tenant-1",
            workspace_id="ws-1",
            project_id="proj-1",
        )
        correlation = CorrelationContext.new()
        query_env = QueryEnvelope(
            request_id=correlation.request_id,
            protocol_version="1.0.0",
            schema_version="1.0",
            request_type="estate.summary",
            kind=RequestKind.QUERY,
            actor=actor,
            correlation=correlation,
            payload={},
        )

        res = caller.handle_query(query_env)
        assert res.status == CallerResultStatus.OK
        data = res.result

        # Assert all required DashboardSummary fields are present
        assert "runningCount" in data
        assert data["runningCount"] == 1
        assert "scheduledCount" in data
        assert "attentionCount" in data
        assert "completedTodayCount" in data
        assert "activeMigrations" in data
        assert len(data["activeMigrations"]) == 1
        assert data["activeMigrations"][0]["name"] == "Test Migration"
        assert data["activeMigrations"][0]["sourceEngine"] == "PostgreSQL"
        assert data["activeMigrations"][0]["targetEngine"] == "Snowflake"
        assert "subsystems" in data
        assert "capacityMetrics" in data
        assert "fleet" in data
        assert "security" in data

        # Zero-fake rule assertion: mTLSEnabled and vaultEncryption are None (unconfigured)
        assert data["security"]["mTLSEnabled"] is None
        assert data["security"]["vaultEncryption"] is None
        assert data["security"]["auditLedgerActive"] is True
        assert data["security"]["posture"] == "partial"

        caller.close()
