"""
akaalIPC.application.router
==============================
The thin IPC router.

Pipeline for every request:

    1. protocol version compatibility check
    2. schema validation
    3. actor/context normalization & structural verification
    4. correlation/causation propagation
    5. command/query dispatch to exactly one UnifiedCallerPort
    6. translate the downstream CallerResult into a ResponseEnvelope
    7. map structured downstream errors as-is; sanitize anything unexpected

The router owns none of: migration state, operation state, capability
truth, readiness, policy, or execution. If ``unified_caller`` is not bound,
every command/query fails closed with ``UNBOUND`` — this is the correct,
deliberate production response, never a stand-in success.
"""

from __future__ import annotations

import datetime
import threading
from typing import Any, Mapping, Optional, Union

from akaalIPC.protocol.envelopes import (
    CommandEnvelope,
    OperationReference,
    QueryEnvelope,
    ResponseEnvelope,
    ResponseStatus,
    SubscriptionBatch,
    SubscriptionRequest,
)
from akaalIPC.protocol.errors import (
    IPCError,
    IPCErrorCategory,
    make_error,
    sanitize_unexpected_exception,
    unbound_error,
)
from akaalIPC.protocol.schemas import RequestKind, SchemaRegistry
from akaalIPC.protocol.versions import check_protocol_compatibility
from akaalIPC.subscriptions.streams import InvalidCursorError, validate_cursor_format
from akaalIPC.transport.ports import (
    CallerResult,
    CallerResultStatus,
    ContextProviderPort,
    SubscriptionSourcePort,
    UnifiedCallerPort,
)

RequestEnvelopeUnion = Union[CommandEnvelope, QueryEnvelope]


class IPCRouter:
    def __init__(
        self,
        *,
        schema_registry: SchemaRegistry,
        unified_caller: Optional[UnifiedCallerPort] = None,
        context_provider: Optional[ContextProviderPort] = None,
        subscription_source: Optional[SubscriptionSourcePort] = None,
    ) -> None:
        self._schema_registry = schema_registry
        self._unified_caller = unified_caller
        self._context_provider = context_provider
        self._subscription_source = subscription_source
        # Guards binding reference changes so binding snapshots are thread-safe
        # without holding locks across external downstream calls.
        self._bindings_lock = threading.Lock()

    # -- production dependency binding -----------------------------------

    def bind_unified_caller(self, unified_caller: UnifiedCallerPort) -> None:
        with self._bindings_lock:
            self._unified_caller = unified_caller

    def bind_context_provider(self, context_provider: ContextProviderPort) -> None:
        with self._bindings_lock:
            self._context_provider = context_provider

    def bind_subscription_source(self, subscription_source: SubscriptionSourcePort) -> None:
        with self._bindings_lock:
            self._subscription_source = subscription_source

    # -- request handling ---------------------------------------------------

    def handle_request(self, envelope: RequestEnvelopeUnion) -> ResponseEnvelope:
        request_id = envelope.request_id
        correlation_id = envelope.correlation.correlation_id

        version_check = check_protocol_compatibility(
            envelope.protocol_version,
            correlation_id=correlation_id,
            request_id=request_id,
        )
        if not version_check.is_compatible:
            return self._error_response(envelope, version_check.error)

        validation = self._schema_registry.validate(
            request_type=envelope.request_type,
            schema_version=envelope.schema_version,
            kind=envelope.kind,
            payload=envelope.payload,
            correlation_id=correlation_id,
            request_id=request_id,
        )
        if not validation.is_valid:
            return self._error_response(envelope, validation.error)

        # Context normalization: envelope.actor was already constructed by
        # the caller/adapter. akaalIPC does not re-derive identity here —
        # a ContextProviderPort is for adapters that hand akaalIPC a raw
        # transport credential rather than a pre-built ActorContext. This
        # router only enforces that *some* actor reference is present.
        if envelope.actor is None or envelope.actor.actor is None:
            return self._error_response(
                envelope,
                make_error(
                    IPCErrorCategory.UNAUTHORIZED,
                    code="MISSING_ACTOR_CONTEXT",
                    message="Request has no actor context.",
                    correlation_id=correlation_id,
                    request_id=request_id,
                ),
            )

        # Snapshot binding reference under lock; release lock before calling downstream.
        with self._bindings_lock:
            unified_caller = self._unified_caller

        if unified_caller is None:
            return self._error_response(
                envelope, unbound_error("UnifiedCallerPort", correlation_id=correlation_id, request_id=request_id)
            )

        try:
            if envelope.kind == RequestKind.COMMAND:
                assert isinstance(envelope, CommandEnvelope)
                result = unified_caller.handle_command(envelope)
            else:
                assert isinstance(envelope, QueryEnvelope)
                result = unified_caller.handle_query(envelope)
        except IPCError as already_structured:
            return self._error_response(envelope, already_structured)
        except Exception as unexpected:  # noqa: BLE001 - boundary sanitization by design
            return self._error_response(
                envelope,
                sanitize_unexpected_exception(
                    unexpected, correlation_id=correlation_id, request_id=request_id
                ),
            )

        return self._translate_caller_result(envelope, result)

    def handle_subscription(self, request: SubscriptionRequest) -> SubscriptionBatch:
        correlation_id = request.correlation.correlation_id if request.correlation else None

        # Structural identity-context check for subscriptions
        if request.actor is None or request.actor.actor is None:
            raise make_error(
                IPCErrorCategory.UNAUTHORIZED,
                code="MISSING_ACTOR_CONTEXT",
                message="Subscription request has no actor context.",
                correlation_id=correlation_id,
            )

        # Snapshot binding reference under lock; release lock before calling downstream.
        with self._bindings_lock:
            subscription_source = self._subscription_source

        if subscription_source is None:
            raise unbound_error(
                "SubscriptionSourcePort", correlation_id=correlation_id
            )

        # Structural IPC-level cursor validation FIRST before delegating downstream
        if request.cursor is not None:
            try:
                validate_cursor_format(request.cursor)
            except InvalidCursorError as err:
                raise make_error(
                    IPCErrorCategory.INVALID_REQUEST,
                    code="INVALID_CURSOR",
                    message=str(err),
                    correlation_id=correlation_id,
                ) from err

            if not subscription_source.validate_cursor(request.subscription_id, request.cursor):
                raise make_error(
                    IPCErrorCategory.INVALID_REQUEST,
                    code="INVALID_CURSOR",
                    message=f"Cursor {request.cursor!r} is not valid for subscription {request.subscription_id!r}.",
                    correlation_id=correlation_id,
                )

        try:
            return subscription_source.fetch(request)
        except IPCError:
            raise
        except Exception as unexpected:  # noqa: BLE001
            raise sanitize_unexpected_exception(
                unexpected, correlation_id=correlation_id
            ) from unexpected

    # -- internal helpers -----------------------------------------------

    def _translate_caller_result(
        self, envelope: RequestEnvelopeUnion, result: CallerResult
    ) -> ResponseEnvelope:
        response_type = f"{envelope.request_type}.response"
        if result.status == CallerResultStatus.OK:
            return ResponseEnvelope(
                request_id=envelope.request_id,
                correlation_id=envelope.correlation.correlation_id,
                protocol_version=envelope.protocol_version,
                schema_version=envelope.schema_version,
                response_type=response_type,
                status=ResponseStatus.OK,
                result=result.result if result.result is not None else {},
            )
        if result.status == CallerResultStatus.ACCEPTED:
            if result.operation is None:
                error = sanitize_unexpected_exception(
                    ValueError("UnifiedCallerPort returned ACCEPTED with no OperationReference"),
                    correlation_id=envelope.correlation.correlation_id,
                    request_id=envelope.request_id,
                )
                return self._error_response(envelope, error)
            return ResponseEnvelope(
                request_id=envelope.request_id,
                correlation_id=envelope.correlation.correlation_id,
                protocol_version=envelope.protocol_version,
                schema_version=envelope.schema_version,
                response_type=response_type,
                status=ResponseStatus.ACCEPTED,
                operation=result.operation,
            )
        # ERROR: pass the downstream's structured error through unchanged,
        # only filling in correlation/request IDs it may not have known.
        error = result.error or sanitize_unexpected_exception(
            ValueError("UnifiedCallerPort returned ERROR status with no IPCError"),
            correlation_id=envelope.correlation.correlation_id,
            request_id=envelope.request_id,
        )
        return self._error_response(envelope, error)

    def _error_response(
        self, envelope: RequestEnvelopeUnion, error: Optional[IPCError]
    ) -> ResponseEnvelope:
        if error is None:
            error = sanitize_unexpected_exception(
                ValueError("router attempted an error response with no IPCError"),
                correlation_id=envelope.correlation.correlation_id,
                request_id=envelope.request_id,
            )
        return ResponseEnvelope(
            request_id=envelope.request_id,
            correlation_id=envelope.correlation.correlation_id,
            protocol_version=envelope.protocol_version,
            schema_version=envelope.schema_version,
            response_type=f"{envelope.request_type}.error",
            status=ResponseStatus.ERROR,
            error=error,
        )
