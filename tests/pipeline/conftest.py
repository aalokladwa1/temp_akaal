"""tests/pipeline/conftest.py
========================
Pytest fixtures and helpers for akaalPipeline test suite.
"""

from __future__ import annotations

import os
import tempfile
import uuid
import pytest

os.environ.setdefault("AKAAL_GATEWAY_RECEIPT_SECRET", "akaal-test-provisioned-secret-v1")

from akaalIPC.protocol.envelopes import CommandEnvelope, QueryEnvelope
from akaalIPC.protocol.schemas import RequestKind
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


def make_command(request_type: str, payload: dict, actor: ActorContext, correlation: CorrelationContext, idempotency_key: str = None) -> CommandEnvelope:
    return CommandEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:12]}",
        command_id=f"cmd-{uuid.uuid4().hex[:12]}",
        request_type=request_type,
        protocol_version="1.0.0",
        schema_version="1.0",
        payload=payload,
        kind=RequestKind.COMMAND,
        actor=actor,
        correlation=correlation,
        idempotency_key=idempotency_key,
    )


def make_query(request_type: str, payload: dict, actor: ActorContext, correlation: CorrelationContext) -> QueryEnvelope:
    return QueryEnvelope(
        request_id=f"req-{uuid.uuid4().hex[:12]}",
        request_type=request_type,
        protocol_version="1.0.0",
        schema_version="1.0",
        payload=payload,
        kind=RequestKind.QUERY,
        actor=actor,
        correlation=correlation,
    )



@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    return path


@pytest.fixture
def sqlite_uow(temp_db_path):
    uow = SQLiteUnitOfWork(db_path=temp_db_path)
    yield uow
    uow.close()


@pytest.fixture
def unified_caller(temp_db_path):
    caller = PipelineUnifiedCaller(db_path=temp_db_path)
    return caller


@pytest.fixture
def ipc_actor():
    return ActorContext(
        actor=ActorReference(actor_id="user-100", actor_type="user", display_name="Test Operator"),
        organization_id="org-acme",
        workspace_id="ws-main",
        project_id="proj-db",
        environment="production",
        roles=("operator", "admin"),
        scopes=("migration.read", "migration.write"),
    )


@pytest.fixture
def pipeline_actor(ipc_actor):
    return PipelineActorContext.from_ipc(ipc_actor)


@pytest.fixture
def ipc_correlation():
    return CorrelationContext.new()
