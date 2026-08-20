"""
akaalIPC.protocol.envelopes
==============================
Typed envelopes for the akaalIPC protocol.

Every value that crosses the boundary is one of the types defined here.
Payloads are restricted to JSON-safe primitives (str/int/float/bool/None,
and mappings/sequences thereof) — this is what makes serialization
deterministic and transport-neutral, and what prevents arbitrary object
construction from untrusted request data (no pickling, no polymorphic
``__class__`` payloads, no eval of caller-supplied code).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalIPC.protocol.errors import IPCError
from akaalIPC.protocol.schemas import RequestKind
from akaalIPC.security.context import ActorContext, CorrelationContext

JsonScalar = (str, int, float, bool, type(None))


class PayloadTypeError(ValueError):
    """Raised when a payload contains a value that is not JSON-safe."""


def assert_json_safe(value: Any, *, path: str = "$") -> None:
    """Recursively verify a value contains only JSON-safe primitives.

    This is the guard that keeps envelope payloads from ever smuggling a
    live Python object (a function, a class, an open file, an exception)
    across the IPC boundary.
    """
    if isinstance(value, JsonScalar):
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PayloadTypeError(f"{path}: mapping keys must be strings, got {type(key).__name__}")
            assert_json_safe(item, path=f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            assert_json_safe(item, path=f"{path}[{index}]")
        return
    raise PayloadTypeError(f"{path}: value of type {type(value).__name__} is not JSON-safe")


@dataclass(frozen=True)
class RequestEnvelope:
    """Base shape shared by every inbound request."""

    request_id: str
    protocol_version: str
    schema_version: str
    request_type: str
    kind: RequestKind
    actor: ActorContext
    correlation: CorrelationContext
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert_json_safe(self.payload)


@dataclass(frozen=True)
class CommandEnvelope(RequestEnvelope):
    """A mutating request. Carries idempotency/optimistic-concurrency
    metadata that only makes sense for commands."""

    command_id: str = ""
    idempotency_key: Optional[str] = None
    expected_revision: Optional[str] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.kind != RequestKind.COMMAND:
            raise ValueError("CommandEnvelope.kind must be RequestKind.COMMAND")
        if not self.command_id:
            raise ValueError("CommandEnvelope.command_id must not be empty")


@dataclass(frozen=True)
class QueryEnvelope(RequestEnvelope):
    """A read-only request. Never carries idempotency/revision semantics."""

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.kind != RequestKind.QUERY:
            raise ValueError("QueryEnvelope.kind must be RequestKind.QUERY")


@dataclass(frozen=True)
class OperationReference:
    """A pointer to canonical, downstream-owned asynchronous work.

    akaalIPC allocates NOTHING about the operation's lifecycle beyond this
    reference — status must always be re-queried from the downstream
    authority via a QueryEnvelope, never inferred locally.
    """

    operation_id: str
    accepted_at: str
    query_request_type: str
    correlation_id: Optional[str] = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.operation_id:
            raise ValueError("OperationReference.operation_id must not be empty")
        if not self.query_request_type:
            raise ValueError(
                "OperationReference.query_request_type must name the request_type "
                "a caller uses to poll this operation."
            )
        assert_json_safe(self.details)


class ResponseStatus(str, enum.Enum):
    OK = "OK"
    ACCEPTED = "ACCEPTED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ErrorEnvelope:
    error: IPCError

    def to_dict(self) -> dict:
        return {"error": self.error.to_dict()}


@dataclass(frozen=True)
class ResponseEnvelope:
    """The single response shape for every command/query.

    Exactly one of ``result`` / ``operation`` / ``error`` is populated,
    matching ``status``. This is enforced in ``__post_init__`` rather than
    relying on callers to only read the "right" field.
    """

    request_id: str
    correlation_id: str
    protocol_version: str
    schema_version: str
    response_type: str
    status: ResponseStatus
    result: Optional[Mapping[str, Any]] = None
    operation: Optional[OperationReference] = None
    error: Optional[IPCError] = None

    def __post_init__(self) -> None:
        populated = [f for f in (self.result, self.operation, self.error) if f is not None]
        if len(populated) != 1:
            raise ValueError(
                "ResponseEnvelope must populate exactly one of result/operation/error, "
                f"got {len(populated)}"
            )
        if self.status == ResponseStatus.OK and self.result is None:
            raise ValueError("ResponseEnvelope.status=OK requires result")
        if self.status == ResponseStatus.ACCEPTED and self.operation is None:
            raise ValueError("ResponseEnvelope.status=ACCEPTED requires operation")
        if self.status == ResponseStatus.ERROR and self.error is None:
            raise ValueError("ResponseEnvelope.status=ERROR requires error")
        if self.result is not None:
            assert_json_safe(self.result)

    def to_dict(self) -> dict:
        base = {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "protocol_version": self.protocol_version,
            "schema_version": self.schema_version,
            "response_type": self.response_type,
            "status": self.status.value,
        }
        if self.result is not None:
            base["result"] = dict(self.result)
        if self.operation is not None:
            base["operation"] = {
                "operation_id": self.operation.operation_id,
                "accepted_at": self.operation.accepted_at,
                "query_request_type": self.operation.query_request_type,
                "correlation_id": self.operation.correlation_id,
                "details": dict(self.operation.details),
            }
        if self.error is not None:
            base["error"] = self.error.to_dict()
        return base


@dataclass(frozen=True)
class EventEnvelope:
    """One durable event, as delivered through a subscription."""

    event_id: str
    event_type: str
    sequence: int
    cursor: str
    occurred_at: str
    correlation_id: Optional[str]
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert_json_safe(self.payload)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "sequence": self.sequence,
            "cursor": self.cursor,
            "occurred_at": self.occurred_at,
            "correlation_id": self.correlation_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class SubscriptionRequest:
    """A caller's request to (re)attach to a durable event stream."""

    subscription_id: str
    filter_descriptor: Mapping[str, Any]
    actor: ActorContext
    correlation: CorrelationContext
    cursor: Optional[str] = None  # None => start from the downstream authority's default

    def __post_init__(self) -> None:
        assert_json_safe(self.filter_descriptor)


@dataclass(frozen=True)
class SubscriptionBatch:
    """One page of durable events returned for a subscription."""

    subscription_id: str
    events: Tuple[EventEnvelope, ...]
    next_cursor: str
    has_more: bool

    def to_dict(self) -> dict:
        return {
            "subscription_id": self.subscription_id,
            "events": [e.to_dict() for e in self.events],
            "next_cursor": self.next_cursor,
            "has_more": self.has_more,
        }
