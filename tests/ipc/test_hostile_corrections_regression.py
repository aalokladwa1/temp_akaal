"""Hostile regression tests for akaalIPC corrections.

Exercises:
1. Malformed cursor structural rejection (prior to downstream calls).
2. Valid structural but invalid semantic cursor rejection.
3. Missing subscription actor context rejection.
4. ActorContext roles immutability & list mutation protection.
5. ActorContext scopes immutability & list mutation protection.
6. Deterministic concurrent UnifiedCallerPort rebind snapshot isolation.
7. Deterministic concurrent SubscriptionSourcePort rebind snapshot isolation.
"""

from __future__ import annotations

import threading
import pytest

from akaalIPC.application.router import IPCRouter
from akaalIPC.protocol.envelopes import SubscriptionRequest
from akaalIPC.protocol.errors import IPCError, IPCErrorCategory
from akaalIPC.protocol.schemas import RequestKind, SchemaDescriptor
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport.ports import CallerResult, CallerResultStatus
from tests.ipc.conftest import RecordingSubscriptionSource, RecordingUnifiedCaller, make_command, make_query


# -- 6.1 Malformed Cursor ----------------------------------------------------


def test_malformed_cursor_fails_before_downstream_calls(schema_registry, actor, correlation):
    """Prove malformed cursor fails closed at structural layer without touching downstream port."""
    source = RecordingSubscriptionSource(valid_cursors={"cursor-1"}, batch_factory=lambda r: None)
    router = IPCRouter(schema_registry=schema_registry, subscription_source=source)

    # Malformed cursor containing path traversal / spaces / illegal chars
    malformed_cursors = [
        "../../../etc/passwd",
        "cursor with spaces",
        "cursor\x00injection",
        "x" * 300,  # > 256 chars
    ]

    for bad_cursor in malformed_cursors:
        request = SubscriptionRequest(
            subscription_id="sub-1",
            filter_descriptor={},
            actor=actor,
            correlation=correlation,
            cursor=bad_cursor,
        )
        with pytest.raises(IPCError) as exc_info:
            router.handle_subscription(request)

        assert exc_info.value.category == IPCErrorCategory.INVALID_REQUEST
        assert exc_info.value.code == "INVALID_CURSOR"
        # Crucial authority assertion: downstream port methods were NEVER called
        assert len(source.fetch_calls) == 0


# -- 6.2 Valid Structural But Invalid Semantic Cursor ------------------------


def test_valid_structural_but_invalid_semantic_cursor(schema_registry, actor, correlation):
    """Prove structurally valid cursor passes regex check but is rejected by downstream authority."""
    # "cursor-999" is structurally valid (matches regex) but NOT in valid_cursors
    source = RecordingSubscriptionSource(valid_cursors={"cursor-100"}, batch_factory=lambda r: None)
    router = IPCRouter(schema_registry=schema_registry, subscription_source=source)

    request = SubscriptionRequest(
        subscription_id="sub-1",
        filter_descriptor={},
        actor=actor,
        correlation=correlation,
        cursor="cursor-999",
    )
    with pytest.raises(IPCError) as exc_info:
        router.handle_subscription(request)

    assert exc_info.value.category == IPCErrorCategory.INVALID_REQUEST
    assert exc_info.value.code == "INVALID_CURSOR"
    assert "Cursor 'cursor-999' is not valid for subscription" in exc_info.value.message
    # Structural check passed, downstream validate_cursor ran, but fetch was NEVER called
    assert len(source.fetch_calls) == 0


# -- 6.3 Missing Subscription Actor ------------------------------------------


def test_missing_subscription_actor_context_rejected(schema_registry, correlation):
    """Prove subscription request without actor context is rejected before downstream port interaction."""
    source = RecordingSubscriptionSource(valid_cursors={"cursor-1"}, batch_factory=lambda r: None)
    router = IPCRouter(schema_registry=schema_registry, subscription_source=source)

    request_no_actor = SubscriptionRequest(
        subscription_id="sub-1",
        filter_descriptor={},
        actor=None,  # type: ignore
        correlation=correlation,
        cursor="cursor-1",
    )

    with pytest.raises(IPCError) as exc_info:
        router.handle_subscription(request_no_actor)

    assert exc_info.value.category == IPCErrorCategory.UNAUTHORIZED
    assert exc_info.value.code == "MISSING_ACTOR_CONTEXT"
    assert "Subscription request has no actor context" in exc_info.value.message
    # Downstream port methods must NOT have been called
    assert len(source.fetch_calls) == 0


# -- 6.4 & 6.5 Actor Roles & Scopes Immutability ------------------------------


def test_actor_context_roles_and_scopes_normalized_and_immutable():
    """Prove passing a list to roles/scopes produces a tuple that resists external list mutation."""
    roles_list = ["operator", "auditor"]
    scopes_list = ["migration.read", "schema.view"]

    ref = ActorReference(actor_id="u-100", actor_type="user")
    ctx = ActorContext(actor=ref, roles=roles_list, scopes=scopes_list)  # type: ignore

    # Assert normalized to tuple
    assert isinstance(ctx.roles, tuple)
    assert isinstance(ctx.scopes, tuple)
    assert ctx.roles == ("operator", "auditor")
    assert ctx.scopes == ("migration.read", "schema.view")

    # Attempt to mutate original caller lists
    roles_list.append("admin")
    scopes_list.append("system.write")

    # Assert ActorContext was NOT altered by external list mutation
    assert ctx.roles == ("operator", "auditor")
    assert ctx.scopes == ("migration.read", "schema.view")


# -- 6.6 Concurrent Rebind Snapshot (UnifiedCallerPort) -----------------------


def test_concurrent_unified_caller_rebind_snapshot_isolation(schema_registry, actor, correlation):
    """Prove in-flight request uses snapshot acquired at start even if router is rebound concurrently."""
    caller_a = RecordingUnifiedCaller()
    caller_b = RecordingUnifiedCaller()

    # Event synchronization to control execution steps deterministically
    request_in_flight = threading.Event()
    rebind_complete = threading.Event()
    finish_request = threading.Event()

    class BlockingCaller:
        def handle_query(self, query):
            caller_a.handle_query(query)
            request_in_flight.set()
            rebind_complete.wait(timeout=5)
            return CallerResult(status=CallerResultStatus.OK, result={"caller": "A"})

        def handle_command(self, command):
            return CallerResult(status=CallerResultStatus.OK, result={})

    blocking_caller = BlockingCaller()
    router = IPCRouter(schema_registry=schema_registry, unified_caller=blocking_caller)  # type: ignore

    result_holder = {}

    def worker_request_a():
        envelope = make_query("echo.query", "1.0", actor, correlation, {"message": "reqA"})
        res = router.handle_request(envelope)
        result_holder["reqA"] = res

    # Start Request A on Thread 1
    t1 = threading.Thread(target=worker_request_a)
    t1.start()

    # Wait until Request A enters handle_query
    assert request_in_flight.wait(timeout=5)

    # Concurrently rebind router on Thread 2 to caller_b
    router.bind_unified_caller(caller_b)
    rebind_complete.set()

    t1.join(timeout=5)

    # Request A must have completed using Caller A's result
    assert result_holder["reqA"].result == {"caller": "A"}

    # Subsequent Request B must use Caller B
    envelope_b = make_query("echo.query", "1.0", actor, CorrelationContext.new(), {"message": "reqB"})
    res_b = router.handle_request(envelope_b)
    assert len(caller_b.received_queries) == 1


# -- 6.7 Concurrent Rebind Snapshot (SubscriptionSourcePort) ------------------


def test_concurrent_subscription_source_rebind_snapshot_isolation(schema_registry, actor, correlation):
    """Prove in-flight subscription uses snapshot acquired at start even if router is rebound concurrently."""
    source_a_calls = []
    source_b = RecordingSubscriptionSource(valid_cursors={"c1"}, batch_factory=lambda r: None)

    sub_in_flight = threading.Event()
    rebind_done = threading.Event()

    class BlockingSubscriptionSource:
        def validate_cursor(self, sub_id, cursor):
            return True

        def fetch(self, request):
            source_a_calls.append(request)
            sub_in_flight.set()
            rebind_done.wait(timeout=5)
            from akaalIPC.protocol.envelopes import SubscriptionBatch
            return SubscriptionBatch(subscription_id=request.subscription_id, events=(), next_cursor="c2", has_more=False)

    blocking_source = BlockingSubscriptionSource()
    router = IPCRouter(schema_registry=schema_registry, subscription_source=blocking_source)  # type: ignore

    batch_holder = {}

    def worker_sub_a():
        req = SubscriptionRequest(subscription_id="sub-1", filter_descriptor={}, actor=actor, correlation=correlation, cursor="c1")
        batch_holder["subA"] = router.handle_subscription(req)

    t1 = threading.Thread(target=worker_sub_a)
    t1.start()

    assert sub_in_flight.wait(timeout=5)

    # Concurrently rebind router to source_b
    router.bind_subscription_source(source_b)
    rebind_done.set()

    t1.join(timeout=5)

    assert batch_holder["subA"].next_cursor == "c2"
    assert len(source_a_calls) == 1
    assert len(source_b.fetch_calls) == 0
