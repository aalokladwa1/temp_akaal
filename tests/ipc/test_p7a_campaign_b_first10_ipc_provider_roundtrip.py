"""
tests.ipc.test_p7a_campaign_b_first10_ipc_provider_roundtrip
======================================================================
P7A Campaign B — First-10-Provider IPC acceptance closure.

akaalIPC is deliberately provider-agnostic: it carries an opaque, JSON-safe payload
and enforces its own structural/security invariants (protocol version, schema
validation, actor presence, correlation propagation, secret non-exposure on error),
never inspecting or special-casing "provider_id". This suite proves, using the REAL
production `IPCRouter` (akaalIPC/application/router.py, unmodified) against the
UnifiedCallerPort seam the router's own docstring designates as its boundary of
responsibility:

  1. Every one of the 10 first-Campaign-B providers' identity survives real
     serialize (envelope construction + assert_json_safe) -> dispatch (IPCRouter ->
     UnifiedCallerPort) -> response (ResponseEnvelope.to_dict()) round-trip, byte for
     byte, without IPC ever needing to know these providers exist.
  2. A non-JSON-safe payload value can never cross the envelope boundary at all
     (PayloadTypeError at construction time), regardless of provider_id.
  3. A malformed operation (missing a schema-required field) is rejected by real
     schema validation BEFORE the downstream caller is ever invoked.
  4. Missing actor context is rejected before dispatch, for every provider.
  5. Correlation ids propagate exactly, in both success and error responses.
  6. An unexpected downstream exception whose message contains a real secret value
     is sanitized -- the secret never appears anywhere in the resulting
     ResponseEnvelope -- proving akaalIPC's existing secret-safety mechanism
     (sanitize_unexpected_exception discarding str(exc)) holds for every provider's
     command, not just a generic one.

Nothing under akaalIPC/** is mocked; only the UnifiedCallerPort seam (the router's
own documented external dependency) uses the shared, pre-existing
RecordingUnifiedCaller test double from tests/ipc/conftest.py.
"""

from __future__ import annotations

import pytest

from akaalIPC.application.router import IPCRouter
from akaalIPC.protocol.envelopes import PayloadTypeError, ResponseStatus
from akaalIPC.protocol.errors import IPCErrorCategory
from akaalIPC.protocol.schemas import RequestKind, SchemaDescriptor, SchemaRegistry
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResult, CallerResultStatus

from tests.ipc.conftest import RecordingUnifiedCaller, make_command

NEW_PROVIDERS = [
    "cockroachdb", "rabbitmq", "pulsar", "dynamodb", "couchbase",
    "clickhouse", "influxdb", "yugabytedb", "tidb", "singlestore",
]


def _validate_bulk_migration(payload):
    if "provider_id" not in payload:
        return "payload must contain 'provider_id'"
    if "migration_id" not in payload:
        return "payload must contain 'migration_id'"
    return None


@pytest.fixture
def bulk_migration_registry() -> SchemaRegistry:
    registry = SchemaRegistry()
    registry.register(
        SchemaDescriptor("bulk_migration.execute", "1.0", RequestKind.COMMAND, _validate_bulk_migration)
    )
    return registry


@pytest.fixture
def actor() -> ActorContext:
    return ActorContext(
        actor=ActorReference(actor_id="user-1", actor_type="user", display_name="Test User"),
        organization_id="org-1",
        workspace_id="ws-1",
    )


def _router(registry, caller):
    return IPCRouter(schema_registry=registry, unified_caller=caller)


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_provider_identity_round_trips_through_real_ipc_dispatch(bulk_migration_registry, actor, provider_id):
    """Real IPCRouter dispatch, for every one of the 10 providers: the SAME generic
    envelope/schema/router machinery used by the original providers carries provider_id
    through construction -> validation -> dispatch -> response unchanged."""
    caller = RecordingUnifiedCaller()
    caller.next_command_result = CallerResult(
        status=CallerResultStatus.OK,
        result={"provider_id": provider_id, "accepted": True},
    )
    router = _router(bulk_migration_registry, caller)
    correlation = CorrelationContext.new()

    envelope = make_command(
        "bulk_migration.execute", "1.0", actor, correlation,
        payload={"provider_id": provider_id, "migration_id": f"mig-{provider_id}"},
    )
    response = router.handle_request(envelope)

    assert response.status == ResponseStatus.OK
    assert response.correlation_id == correlation.correlation_id
    assert len(caller.received_commands) == 1
    assert caller.received_commands[0].payload["provider_id"] == provider_id
    assert response.to_dict()["result"]["provider_id"] == provider_id


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_non_json_safe_payload_rejected_before_envelope_construction(bulk_migration_registry, actor, provider_id):
    """A live Python object smuggled into the payload (here, a function) must never
    cross the IPC boundary for ANY provider -- assert_json_safe fails closed at
    envelope construction, before the router or downstream caller ever sees it."""
    correlation = CorrelationContext.new()
    with pytest.raises(PayloadTypeError):
        make_command(
            "bulk_migration.execute", "1.0", actor, correlation,
            payload={"provider_id": provider_id, "migration_id": "m1", "bad": lambda: None},
        )


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_malformed_operation_rejected_before_downstream_dispatch(bulk_migration_registry, actor, provider_id):
    """A payload missing the schema-required 'migration_id' field must be rejected by
    real schema validation for every provider, and the downstream UnifiedCallerPort
    must never be invoked -- proving rejection happens strictly before dispatch."""
    caller = RecordingUnifiedCaller()
    router = _router(bulk_migration_registry, caller)
    correlation = CorrelationContext.new()

    envelope = make_command(
        "bulk_migration.execute", "1.0", actor, correlation,
        payload={"provider_id": provider_id},  # missing migration_id
    )
    response = router.handle_request(envelope)

    assert response.status == ResponseStatus.ERROR
    assert caller.received_commands == [], "downstream caller must not be invoked for a malformed operation"


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_missing_actor_context_rejected_before_downstream_dispatch(bulk_migration_registry, provider_id):
    """A command with no actor reference must be rejected (UNAUTHORIZED /
    MISSING_ACTOR_CONTEXT) before the downstream caller is invoked, for every provider --
    provider identity never bypasses actor-presence enforcement."""
    caller = RecordingUnifiedCaller()
    router = _router(bulk_migration_registry, caller)
    correlation = CorrelationContext.new()

    no_actor = ActorContext(actor=None, organization_id="org-1", workspace_id="ws-1")
    envelope = make_command(
        "bulk_migration.execute", "1.0", no_actor, correlation,
        payload={"provider_id": provider_id, "migration_id": "m1"},
    )
    response = router.handle_request(envelope)

    assert response.status == ResponseStatus.ERROR
    assert response.error.code == "MISSING_ACTOR_CONTEXT"
    assert response.error.category == IPCErrorCategory.UNAUTHORIZED
    assert caller.received_commands == []


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_correlation_id_propagates_exactly_in_success_and_error_responses(bulk_migration_registry, actor, provider_id):
    """The correlation id supplied by the caller must appear, unchanged, in both a
    successful response and an error response, for every provider -- correlation
    propagation is never provider-conditional."""
    caller = RecordingUnifiedCaller()
    router = _router(bulk_migration_registry, caller)

    ok_correlation = CorrelationContext.new()
    ok_envelope = make_command(
        "bulk_migration.execute", "1.0", actor, ok_correlation,
        payload={"provider_id": provider_id, "migration_id": "m1"},
    )
    ok_response = router.handle_request(ok_envelope)
    assert ok_response.correlation_id == ok_correlation.correlation_id

    err_correlation = CorrelationContext.new()
    err_envelope = make_command(
        "bulk_migration.execute", "1.0", actor, err_correlation,
        payload={"provider_id": provider_id},  # malformed -> error path
    )
    err_response = router.handle_request(err_envelope)
    assert err_response.correlation_id == err_correlation.correlation_id
    assert err_response.error.correlation_id == err_correlation.correlation_id


@pytest.mark.parametrize("provider_id", NEW_PROVIDERS)
def test_secret_in_unexpected_exception_never_leaks_into_response(bulk_migration_registry, actor, provider_id):
    """A downstream failure whose raw exception message contains a real secret value
    must never expose that secret in the ResponseEnvelope, for any provider --
    proving akaalIPC's existing sanitize_unexpected_exception() (which keeps only
    exception TYPE, never message text) actually holds under a provider-specific
    hostile payload, not merely for a generic 'echo' example."""
    caller = RecordingUnifiedCaller()
    secret_value = "AKIA-FAKE-SECRET-VALUE-DO-NOT-LEAK-12345"
    caller.raise_on_command = RuntimeError(f"connection failed for provider={provider_id} using secret={secret_value}")
    router = _router(bulk_migration_registry, caller)
    correlation = CorrelationContext.new()

    envelope = make_command(
        "bulk_migration.execute", "1.0", actor, correlation,
        payload={"provider_id": provider_id, "migration_id": "m1", "secret_token": secret_value},
    )
    response = router.handle_request(envelope)

    assert response.status == ResponseStatus.ERROR
    serialized = str(response.to_dict())
    assert secret_value not in serialized, "raw secret value must never appear in the sanitized IPC response"
    assert response.error.category == IPCErrorCategory.INTERNAL_ERROR
    assert response.error.details.get("exception_type") == "RuntimeError"
