"""
akaalIPC: the AKAAL production communication boundary.
=====================================================================

akaalIPC is a transport-neutral, versioned, typed, fail-closed protocol
boundary between present/future AKAAL callers (Tauri UI, CLI, REST,
Assistant, plugins) and the canonical downstream application layer (the
future ``akaalPipeline`` -> ``akaalEngine``).

Package map:

    protocol/       typed envelopes, schema registry, version negotiation,
                     structured error taxonomy
    security/       transport-neutral actor/correlation context models
    application/     the thin IPCRouter
    transport/      port contracts future adapters and the downstream
                     application boundary implement against
    subscriptions/  durable-subscription/cursor contract helpers

akaalIPC owns the protocol. It does not own migration state, execution
state, capability truth, policy, or the engine. See each submodule's
docstring for its authority boundary.
"""

from akaalIPC.application import IPCRouter
from akaalIPC.protocol import (
    CURRENT_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    CommandEnvelope,
    IPCError,
    IPCErrorCategory,
    OperationReference,
    QueryEnvelope,
    RequestKind,
    ResponseEnvelope,
    ResponseStatus,
    SchemaDescriptor,
    SchemaRegistry,
)
from akaalIPC.security import ActorContext, ActorReference, CorrelationContext
from akaalIPC.transport import CallerResult, CallerResultStatus, UnifiedCallerPort

__all__ = [
    "IPCRouter",
    "CURRENT_PROTOCOL_VERSION",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "CommandEnvelope",
    "IPCError",
    "IPCErrorCategory",
    "OperationReference",
    "QueryEnvelope",
    "RequestKind",
    "ResponseEnvelope",
    "ResponseStatus",
    "SchemaDescriptor",
    "SchemaRegistry",
    "ActorContext",
    "ActorReference",
    "CorrelationContext",
    "CallerResult",
    "CallerResultStatus",
    "UnifiedCallerPort",
]
