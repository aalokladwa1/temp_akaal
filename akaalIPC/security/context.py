"""
akaalIPC.security.context
============================
Transport-neutral caller context models.

These types NORMALIZE context that has already been established by a real
upstream authority (a transport adapter, a session manager, a future P7
identity system). They deliberately do not:

  - authenticate a user or service;
  - authorize a command;
  - fabricate roles or claims;
  - mark a request as trusted because it arrived on a local transport.

A ``ContextProviderPort`` implementation (bound at startup by whatever
transport hosts akaalIPC) is responsible for turning a raw transport-level
credential/session into an ``ActorContext``. If that provider cannot
produce one, the caller-facing behavior is fail-closed (see
``application.router``), never a fabricated anonymous/default identity.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple


@dataclass(frozen=True)
class ActorReference:
    """Identifies who/what is making the call, as asserted by an upstream authority."""

    actor_id: str
    actor_type: str  # e.g. "user", "service", "plugin", "system"
    display_name: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("ActorReference.actor_id must not be empty")
        if not self.actor_type:
            raise ValueError("ActorReference.actor_type must not be empty")


@dataclass(frozen=True)
class ActorContext:
    """Normalized, transport-neutral caller identity and scoping.

    This carries *references*, not authority. Whether ``roles``/``scopes``
    actually grant permission for a given command is a downstream policy
    decision (explicitly out of scope for akaalIPC per the authority
    boundary in the package README).
    """

    actor: ActorReference
    organization_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    environment: Optional[str] = None
    roles: Tuple[str, ...] = field(default_factory=tuple)
    scopes: Tuple[str, ...] = field(default_factory=tuple)
    session_id: Optional[str] = None
    provenance: Optional[str] = None  # e.g. "tauri-local", "rest-jwt", "cli-token"

    def __post_init__(self) -> None:
        object.__setattr__(self, "roles", tuple(self.roles) if self.roles else ())
        object.__setattr__(self, "scopes", tuple(self.scopes) if self.scopes else ())



@dataclass(frozen=True)
class CorrelationContext:
    """First-class correlation/causation identity for one request.

    ``request_id`` is transport/request-scoped and MAY be allocated by
    akaalIPC itself when a caller does not supply one. ``correlation_id``
    and ``causation_id`` are preserved verbatim when supplied by the
    caller — akaalIPC never silently replaces an incoming, valid
    correlation identity.
    """

    request_id: str
    correlation_id: str
    causation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def new(cls, *, causation_id: Optional[str] = None) -> "CorrelationContext":
        """Allocate a fresh, IPC-owned correlation context for a root request."""
        request_id = f"req-{uuid.uuid4().hex}"
        return cls(
            request_id=request_id,
            correlation_id=f"corr-{uuid.uuid4().hex}",
            causation_id=causation_id,
        )

    @classmethod
    def continuing(
        cls,
        *,
        request_id: Optional[str],
        correlation_id: Optional[str],
        causation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> "CorrelationContext":
        """Build a correlation context from caller-supplied identifiers,
        allocating only the pieces the caller omitted. Never overwrites a
        caller-supplied correlation_id/causation_id."""
        return cls(
            request_id=request_id or f"req-{uuid.uuid4().hex}",
            correlation_id=correlation_id or f"corr-{uuid.uuid4().hex}",
            causation_id=causation_id,
            trace_id=trace_id,
            span_id=span_id,
        )


class MissingActorContextError(ValueError):
    """Raised by a ContextProviderPort implementation when required identity
    context cannot be established. The router converts this into an
    UNAUTHORIZED IPCError — it must never be swallowed into an anonymous
    ActorContext."""
