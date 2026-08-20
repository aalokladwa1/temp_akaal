import pytest

from akaalIPC.application.router import IPCRouter
from akaalIPC.protocol.envelopes import (
    OperationReference,
    ResponseStatus,
)
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory, make_error
from akaalIPC.protocol.schemas import RequestKind, SchemaDescriptor
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResult, CallerResultStatus

from tests.ipc.conftest import RecordingSubscriptionSource, RecordingUnifiedCaller, make_command, make_query


# -- 1/2/3: valid command routing, valid query routing, command/query distinction ----


def test_valid_query_routing(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    envelope = make_query("echo.query", "1.0", actor, correlation, {"message": "hi"})
    response = router.handle_request(envelope)
    assert response.status == ResponseStatus.OK
    assert response.result == {"ok": True}
    assert len(recording_caller.received_queries) == 1
    assert len(recording_caller.received_commands) == 0


def test_valid_command_routing(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    envelope = make_command("widget.create", "1.0", actor, correlation, {"name": "w1"})
    response = router.handle_request(envelope)
    assert response.status == ResponseStatus.OK
    assert len(recording_caller.received_commands) == 1
    assert len(recording_caller.received_queries) == 0


def test_command_and_query_are_not_cross_dispatched(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "x"}))
    router.handle_request(
        make_command("widget.create", "1.0", ActorContext(actor=ActorReference("u2", "user")), CorrelationContext.new(), {"name": "y"})
    )
    assert len(recording_caller.received_queries) == 1
    assert len(recording_caller.received_commands) == 1


# -- 5/6: unknown request type / invalid schema rejection ----


def test_unknown_request_type_rejection(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    envelope = make_query("does.not.exist", "1.0", actor, correlation, {})
    response = router.handle_request(envelope)
    assert response.status == ResponseStatus.ERROR
    assert response.error.code == "UNKNOWN_REQUEST_TYPE"
    assert len(recording_caller.received_queries) == 0


def test_invalid_schema_rejection(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    envelope = make_query("echo.query", "1.0", actor, correlation, {"message": 12345})  # wrong type
    response = router.handle_request(envelope)
    assert response.status == ResponseStatus.ERROR
    assert response.error.category == IPCErrorCategory.INVALID_SCHEMA
    assert len(recording_caller.received_queries) == 0


def test_schema_incompatibility_rejection(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    envelope = make_query("echo.query", "9.9", actor, correlation, {"message": "hi"})
    response = router.handle_request(envelope)
    assert response.status == ResponseStatus.ERROR
    assert response.error.code == "SCHEMA_VERSION_INCOMPATIBLE"


# -- 7: protocol incompatibility rejection ----


def test_protocol_incompatibility_rejection(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    envelope = make_query("echo.query", "1.0", actor, correlation, {"message": "hi"})
    object.__setattr__(envelope, "protocol_version", "0.0.1")
    response = router.handle_request(envelope)
    assert response.status == ResponseStatus.ERROR
    assert response.error.category == IPCErrorCategory.PROTOCOL_INCOMPATIBLE
    assert len(recording_caller.received_queries) == 0


# -- 10/11/12: actor context, correlation, causation propagation ----


def test_actor_context_propagation(schema_registry, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    actor = ActorContext(actor=ActorReference(actor_id="specific-user", actor_type="user"))
    router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert recording_caller.received_queries[0].actor.actor.actor_id == "specific-user"


def test_correlation_propagation(schema_registry, actor, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    correlation = CorrelationContext.continuing(
        request_id="req-fixed", correlation_id="corr-fixed", causation_id="cause-fixed"
    )
    router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    received = recording_caller.received_queries[0]
    assert received.correlation.correlation_id == "corr-fixed"
    assert received.correlation.request_id == "req-fixed"


def test_causation_propagation(schema_registry, actor, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    correlation = CorrelationContext.continuing(
        request_id="req-1", correlation_id="corr-1", causation_id="cause-parent-op"
    )
    router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert recording_caller.received_queries[0].correlation.causation_id == "cause-parent-op"


def test_correlation_id_never_silently_replaced(schema_registry, actor, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    correlation = CorrelationContext.continuing(request_id=None, correlation_id="caller-supplied-corr")
    response = router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert response.correlation_id == "caller-supplied-corr"


# -- 13: downstream structured error mapping ----


def test_downstream_structured_error_mapping(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    recording_caller.next_query_result = CallerResult(
        status=CallerResultStatus.ERROR,
        error=make_error(IPCErrorCategory.NOT_READY, code="MIGRATION_NOT_READY", message="not ready yet"),
    )
    response = router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert response.status == ResponseStatus.ERROR
    assert response.error.code == "MIGRATION_NOT_READY"
    assert response.error.category == IPCErrorCategory.NOT_READY


# -- 14/15: unexpected exception sanitization, no leakage ----


def test_unexpected_exception_from_downstream_is_sanitized(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    recording_caller.raise_on_query = RuntimeError("db password=hunter2 leaked-in-exception")
    response = router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert response.status == ResponseStatus.ERROR
    assert response.error.category == IPCErrorCategory.INTERNAL_ERROR
    assert "hunter2" not in response.error.message
    assert "hunter2" not in str(response.error.details)


def test_ipc_error_raised_by_caller_passes_through_structured(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    recording_caller.raise_on_query = make_error(IPCErrorCategory.FORBIDDEN, code="NO_ACCESS", message="nope")
    response = router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert response.error.code == "NO_ACCESS"
    assert response.error.category == IPCErrorCategory.FORBIDDEN


# -- 16/17: unbound unified caller / subscription source fail closed ----


def test_unbound_unified_caller_fails_closed(schema_registry, actor, correlation):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=None)
    response = router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert response.status == ResponseStatus.ERROR
    assert response.error.category == IPCErrorCategory.UNBOUND


def test_unbound_subscription_source_fails_closed(schema_registry, actor, correlation):
    from akaalIPC.protocol.envelopes import SubscriptionRequest

    router = IPCRouter(schema_registry=schema_registry, subscription_source=None)
    request = SubscriptionRequest(
        subscription_id="sub-1", filter_descriptor={}, actor=actor, correlation=correlation
    )
    with pytest.raises(IPCError) as exc_info:
        router.handle_subscription(request)
    assert exc_info.value.category == IPCErrorCategory.UNBOUND


# -- 18/19: operation reference round trip, no local completion inference ----


def test_command_returning_accepted_yields_operation_reference(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    op = OperationReference(
        operation_id="op-abc",
        accepted_at="2026-08-20T00:00:00Z",
        query_request_type="widget.create.operation.status",
    )
    recording_caller.next_command_result = CallerResult(status=CallerResultStatus.ACCEPTED, operation=op)
    response = router.handle_request(make_command("widget.create", "1.0", actor, correlation, {"name": "w"}))
    assert response.status == ResponseStatus.ACCEPTED
    assert response.operation.operation_id == "op-abc"
    # The response contains a reference to re-query, never a RUNNING/COMPLETED verdict.
    assert response.result is None


def test_accepted_without_operation_reference_is_sanitized_not_faked(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    recording_caller.next_command_result = CallerResult(status=CallerResultStatus.ACCEPTED, operation=None)
    response = router.handle_request(make_command("widget.create", "1.0", actor, correlation, {"name": "w"}))
    assert response.status == ResponseStatus.ERROR
    assert response.error.category == IPCErrorCategory.INTERNAL_ERROR


# -- 20/21/22: subscription cursor/replay contract ----


def test_subscription_batch_returned_for_valid_cursor(schema_registry, actor, correlation):
    from akaalIPC.protocol.envelopes import SubscriptionBatch, SubscriptionRequest

    def factory(request):
        return SubscriptionBatch(subscription_id=request.subscription_id, events=(), next_cursor="cursor-2", has_more=False)

    source = RecordingSubscriptionSource(valid_cursors={"cursor-1"}, batch_factory=factory)
    router = IPCRouter(schema_registry=schema_registry, subscription_source=source)
    request = SubscriptionRequest(
        subscription_id="sub-1", filter_descriptor={}, actor=actor, correlation=correlation, cursor="cursor-1"
    )
    batch = router.handle_subscription(request)
    assert batch.next_cursor == "cursor-2"
    assert len(source.fetch_calls) == 1


def test_reconnect_with_prior_cursor_replays_from_authoritative_source(schema_registry, actor):
    from akaalIPC.protocol.envelopes import SubscriptionBatch, SubscriptionRequest

    def factory(request):
        return SubscriptionBatch(subscription_id=request.subscription_id, events=(), next_cursor="cursor-3", has_more=False)

    source = RecordingSubscriptionSource(valid_cursors={"cursor-2"}, batch_factory=factory)
    router = IPCRouter(schema_registry=schema_registry, subscription_source=source)

    # First connection ends with next_cursor="cursor-2" (simulated). Client disconnects.
    # Reconnect: client supplies the durable cursor it was last given.
    reconnect_request = SubscriptionRequest(
        subscription_id="sub-1",
        filter_descriptor={},
        actor=actor,
        correlation=CorrelationContext.new(),
        cursor="cursor-2",
    )
    batch = router.handle_subscription(reconnect_request)
    assert batch.next_cursor == "cursor-3"


def test_invalid_cursor_rejected(schema_registry, actor, correlation):
    from akaalIPC.protocol.envelopes import SubscriptionRequest

    source = RecordingSubscriptionSource(valid_cursors={"cursor-1"}, batch_factory=lambda r: None)
    router = IPCRouter(schema_registry=schema_registry, subscription_source=source)
    request = SubscriptionRequest(
        subscription_id="sub-1", filter_descriptor={}, actor=actor, correlation=correlation, cursor="garbage-cursor"
    )
    with pytest.raises(IPCError) as exc_info:
        router.handle_subscription(request)
    assert exc_info.value.code == "INVALID_CURSOR"
    assert len(source.fetch_calls) == 0


# -- 26/27/28: no direct engine/connector/UI imports from akaalIPC ----


def test_router_module_has_no_engine_or_connector_or_ui_imports():
    import ast
    import inspect

    from akaalIPC.application import router as router_module

    tree = ast.parse(inspect.getsource(router_module))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_prefixes = ("akaal.engine", "akaal.gateway", "akaal.connectors", "akaal.cdc", "akaal.validation")
    for module in imported_modules:
        for forbidden in forbidden_prefixes:
            assert not module.startswith(forbidden), f"router.py must not import {module}"


# -- 30: router performs no canonical state mutation ----


def test_router_holds_no_operation_state_between_calls(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    op = OperationReference(operation_id="op-1", accepted_at="now", query_request_type="widget.status")
    recording_caller.next_command_result = CallerResult(status=CallerResultStatus.ACCEPTED, operation=op)
    router.handle_request(make_command("widget.create", "1.0", actor, correlation, {"name": "w"}))

    # The router itself must expose no operation/status store — it is not
    # a canonical state authority. (Only its declared bindings are stateful.)
    instance_attrs = {
        name for name in vars(router) if not name.startswith("_bindings_lock")
    }
    disallowed_state_attrs = {"_operations", "_operation_store", "_state", "_status_map"}
    assert instance_attrs.isdisjoint(disallowed_state_attrs)


# -- hostile: malformed correlation / actor context ----


def test_malformed_actor_context_rejected_at_construction():
    with pytest.raises(ValueError):
        ActorReference(actor_id="", actor_type="user")


# -- hostile: mismatched request/payload type already covered by
# test_request_kind_mismatch_rejected in test_schemas.py; router-level check: ----


def test_router_rejects_unsupported_command(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    # "echo.query" is registered as QUERY; sending it wrapped as a command-shaped
    # request is rejected at the schema layer before ever reaching the caller.
    from akaalIPC.protocol.envelopes import CommandEnvelope

    envelope = CommandEnvelope(
        request_id=correlation.request_id,
        protocol_version="1.0.0",
        schema_version="1.0",
        request_type="echo.query",
        kind=RequestKind.COMMAND,
        actor=actor,
        correlation=correlation,
        payload={"message": "hi"},
        command_id="cmd-x",
    )
    response = router.handle_request(envelope)
    assert response.status == ResponseStatus.ERROR
    assert response.error.code == "REQUEST_KIND_MISMATCH"
    assert len(recording_caller.received_commands) == 0


def test_router_rejects_unsupported_query(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    response = router.handle_request(make_query("no.such.query", "1.0", actor, correlation, {}))
    assert response.status == ResponseStatus.ERROR
    assert response.error.code == "UNKNOWN_REQUEST_TYPE"


def test_downstream_timeout_reported_not_hung(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    recording_caller.raise_on_query = make_error(IPCErrorCategory.TIMEOUT, code="DOWNSTREAM_TIMEOUT", message="timed out")
    response = router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert response.error.category == IPCErrorCategory.TIMEOUT
    assert response.error.retryable is True


def test_downstream_cancellation_reported(schema_registry, actor, correlation, recording_caller):
    router = IPCRouter(schema_registry=schema_registry, unified_caller=recording_caller)
    recording_caller.raise_on_query = make_error(IPCErrorCategory.CANCELLED, code="OP_CANCELLED", message="cancelled")
    response = router.handle_request(make_query("echo.query", "1.0", actor, correlation, {"message": "hi"}))
    assert response.error.category == IPCErrorCategory.CANCELLED


def test_reconnect_after_router_recreation_still_replays_via_downstream_authority(schema_registry, actor):
    """akaalIPC holds no state itself — a brand-new IPCRouter instance,
    wired to the same durable SubscriptionSourcePort, must still be able to
    resume a subscription from a cursor issued by a previous router
    instance. This proves the router is not where durability lives."""
    from akaalIPC.protocol.envelopes import SubscriptionBatch, SubscriptionRequest

    def factory(request):
        return SubscriptionBatch(subscription_id=request.subscription_id, events=(), next_cursor="cursor-9", has_more=False)

    shared_durable_source = RecordingSubscriptionSource(valid_cursors={"cursor-8"}, batch_factory=factory)

    router_a = IPCRouter(schema_registry=schema_registry, subscription_source=shared_durable_source)
    del router_a  # simulate the first router instance going away entirely

    router_b = IPCRouter(schema_registry=schema_registry, subscription_source=shared_durable_source)
    request = SubscriptionRequest(
        subscription_id="sub-1", filter_descriptor={}, actor=actor, correlation=CorrelationContext.new(), cursor="cursor-8"
    )
    batch = router_b.handle_subscription(request)
    assert batch.next_cursor == "cursor-9"


def test_no_fake_success_fallback_when_binding_missing(schema_registry, actor, correlation):
    """Even with a schema-valid request, an unbound caller must never
    produce a status=OK response — this is the core zero-fake invariant."""
    router = IPCRouter(schema_registry=schema_registry, unified_caller=None)
    response = router.handle_request(make_command("widget.create", "1.0", actor, correlation, {"name": "w"}))
    assert response.status != ResponseStatus.OK
    assert response.status == ResponseStatus.ERROR
