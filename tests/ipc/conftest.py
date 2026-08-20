"""Shared, test-only deterministic doubles for akaalIPC tests.

Nothing in this file is imported by production code (nothing under
``akaalIPC/**``). These fixtures exist strictly to exercise
``akaalIPC.application.router.IPCRouter`` against the ports it depends on.
"""

from __future__ import annotations

import pytest

from akaalIPC.protocol.envelopes import (
    CommandEnvelope,
    OperationReference,
    QueryEnvelope,
)
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error
from akaalIPC.protocol.schemas import RequestKind, SchemaDescriptor, SchemaRegistry
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResult, CallerResultStatus


def _validate_echo(payload):
    if "message" not in payload:
        return "payload must contain 'message'"
    if not isinstance(payload["message"], str):
        return "'message' must be a string"
    return None


def _validate_create_widget(payload):
    if "name" not in payload:
        return "payload must contain 'name'"
    return None


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    registry = SchemaRegistry()
    registry.register(SchemaDescriptor("echo.query", "1.0", RequestKind.QUERY, _validate_echo))
    registry.register(
        SchemaDescriptor("widget.create", "1.0", RequestKind.COMMAND, _validate_create_widget)
    )
    return registry


@pytest.fixture
def actor() -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id="user-1", actor_type="user", display_name="Test User"),
        organization_id="org-1",
        workspace_id="ws-1",
    )


@pytest.fixture
def correlation() -> CorrelationContext:
    return CorrelationContext.new()


def make_query(request_type, schema_version, actor, correlation, payload):
    return QueryEnvelope(
        request_id=correlation.request_id,
        protocol_version="1.0.0",
        schema_version=schema_version,
        request_type=request_type,
        kind=RequestKind.QUERY,
        actor=actor,
        correlation=correlation,
        payload=payload,
    )


def make_command(request_type, schema_version, actor, correlation, payload, *, command_id="cmd-1", idempotency_key=None):
    return CommandEnvelope(
        request_id=correlation.request_id,
        protocol_version="1.0.0",
        schema_version=schema_version,
        request_type=request_type,
        kind=RequestKind.COMMAND,
        actor=actor,
        correlation=correlation,
        payload=payload,
        command_id=command_id,
        idempotency_key=idempotency_key,
    )


class RecordingUnifiedCaller:
    """Deterministic test double for UnifiedCallerPort.

    Records every command/query it receives so tests can assert on actor
    and correlation propagation, and can be configured up-front to return
    OK / ACCEPTED / ERROR / raise, to exercise every router branch.
    """

    def __init__(self):
        self.received_commands = []
        self.received_queries = []
        self.next_command_result = CallerResult(status=CallerResultStatus.OK, result={"ok": True})
        self.next_query_result = CallerResult(status=CallerResultStatus.OK, result={"ok": True})
        self.raise_on_command: Exception | None = None
        self.raise_on_query: Exception | None = None

    def handle_command(self, command: CommandEnvelope) -> CallerResult:
        self.received_commands.append(command)
        if self.raise_on_command is not None:
            raise self.raise_on_command
        return self.next_command_result

    def handle_query(self, query: QueryEnvelope) -> CallerResult:
        self.received_queries.append(query)
        if self.raise_on_query is not None:
            raise self.raise_on_query
        return self.next_query_result


class RecordingSubscriptionSource:
    """Deterministic test double for SubscriptionSourcePort."""

    def __init__(self, *, valid_cursors=None, batch_factory=None):
        self.valid_cursors = valid_cursors or set()
        self.batch_factory = batch_factory
        self.fetch_calls = []

    def validate_cursor(self, subscription_id, cursor):
        return cursor in self.valid_cursors

    def fetch(self, request):
        self.fetch_calls.append(request)
        return self.batch_factory(request)


@pytest.fixture
def recording_caller() -> RecordingUnifiedCaller:
    return RecordingUnifiedCaller()
