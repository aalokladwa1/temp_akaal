"""
akaalIPC.transport.ports
===========================
Transport-neutral contracts for future adapters and the future downstream
application boundary.

Nothing in this module imports a concrete transport (Tauri/HTTP/CLI) or a
concrete downstream implementation. These are ``typing.Protocol`` contracts —
structural interfaces that real bindings implement and that
``application.router.IPCRouter`` is constructed against.

Binding one of these to a concrete implementation is a production startup
concern, not an akaalIPC concern: see the "PRODUCTION DEPENDENCY BINDING"
requirement — akaalIPC ships the ports, not the bindings.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

from akaalIPC.protocol.envelopes import (
    CommandEnvelope,
    EventEnvelope,
    OperationReference,
    QueryEnvelope,
    ResponseEnvelope,
    SubscriptionBatch,
    SubscriptionRequest,
)
from akaalIPC.protocol.errors import IPCError
from akaalIPC.security.context import ActorContext


class CallerResultStatus(str, enum.Enum):
    OK = "OK"
    ACCEPTED = "ACCEPTED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CallerResult:
    """What a ``UnifiedCallerPort`` implementation returns for one
    command/query. This is the canonical application-layer result the
    router converts into a ``ResponseEnvelope`` — it is intentionally the
    same tri-state shape (ok/accepted/error) as the response envelope, so
    the router's mapping step has no business logic in it, only a
    structural translation.
    """

    status: CallerResultStatus
    result: Optional[Mapping[str, Any]] = None
    operation: Optional[OperationReference] = None
    error: Optional[IPCError] = None


@runtime_checkable
class UnifiedCallerPort(Protocol):
    """The single downstream application boundary akaalIPC routes to.

    A future ``akaalPipeline`` binds this. akaalIPC has no knowledge of
    what implements it — it must not import a pipeline, an engine, a
    gateway, or a connector to type-check against this protocol.
    """

    def handle_command(self, command: CommandEnvelope) -> CallerResult: ...

    def handle_query(self, query: QueryEnvelope) -> CallerResult: ...


@runtime_checkable
class ContextProviderPort(Protocol):
    """Normalizes a raw, transport-supplied credential/session into an
    ``ActorContext``. Must raise
    ``akaalIPC.security.context.MissingActorContextError`` (not return a
    fabricated/anonymous context) when it cannot establish real identity
    for a request that requires one.
    """

    def normalize(self, raw_context: Mapping[str, Any]) -> ActorContext: ...


@runtime_checkable
class SubscriptionSourcePort(Protocol):
    """The durable, downstream-owned source of truth for event history.

    akaalIPC never stores event history itself — every subscription
    fetch/resume is answered by asking this port, which is expected to be
    backed by a real durable store (outbox table, log, etc.) once bound.
    """

    def validate_cursor(self, subscription_id: str, cursor: Optional[str]) -> bool: ...

    def fetch(self, request: SubscriptionRequest) -> SubscriptionBatch: ...


@runtime_checkable
class IPCRequestHandlerPort(Protocol):
    """The transport-facing entrypoint a future adapter (Tauri command
    handler, REST controller, CLI verb, Assistant tool) calls into.
    Implemented by ``application.router.IPCRouter`` — adapters depend on
    this Protocol, not on the concrete router class, so the router's
    internals can change without touching adapter code.
    """

    def handle_request(self, envelope: CommandEnvelope | QueryEnvelope) -> ResponseEnvelope: ...

    def handle_subscription(self, request: SubscriptionRequest) -> SubscriptionBatch: ...
