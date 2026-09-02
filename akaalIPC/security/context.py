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
from typing import Any, Mapping, Optional, Tuple


@dataclass(frozen=True)
class ActorReference:
    """Identifies who/what is making the call, as asserted by an upstream authority."""

    actor_id: str
    actor_type: str  # e.g. "HUMAN", "SERVICE", "WORKLOAD", "MACHINE", "SYSTEM"
    display_name: Optional[str] = None
    email: Optional[str] = None
    trust_domain: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("ActorReference.actor_id must not be empty")
        if not self.actor_type:
            raise ValueError("ActorReference.actor_type must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "display_name": self.display_name,
            "email": self.email,
            "trust_domain": self.trust_domain,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ActorReference:
        return cls(
            actor_id=data["actor_id"],
            actor_type=data["actor_type"],
            display_name=data.get("display_name"),
            email=data.get("email"),
            trust_domain=data.get("trust_domain"),
        )


@dataclass(frozen=True)
class ActorContext:
    """Normalized, transport-neutral caller identity, zero-trust state, and scoping.

    This carries *references and claims*, not authorization authority.
    Whether ``roles``/``scopes`` actually grant permission for a given command is
    a downstream policy decision owned strictly by the canonical P5 authorization authority.
    """

    actor: ActorReference
    organization_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    environment: Optional[str] = None
    roles: Tuple[str, ...] = field(default_factory=tuple)
    scopes: Tuple[str, ...] = field(default_factory=tuple)
    session_id: Optional[str] = None
    session_token: Optional[str] = None  # raw bearer credential presented alongside session_id; NEVER trusted on its own -- only meaningful when resolved through the owning trusted session authority
    provenance: Optional[str] = None  # e.g. "tauri-local", "rest-jwt", "cli-token", "spiffe"

    # Zero-Trust P7 Canonical Dimensions (Decoupled & Provenance-Preserving)
    credential_mechanism: str = "SYSTEM_INTERNAL"
    authentication_state: str = "UNAUTHENTICATED"
    authentication_assurance: str = "NONE"
    trust_domain: Optional[str] = None
    federation_provenance: Optional[Mapping[str, Any]] = None
    workload_identity: Optional[str] = None
    original_actor: Optional[ActorReference] = None
    calling_workload: Optional[str] = None
    target_workload: Optional[str] = None
    issued_at: Optional[str] = None
    expires_at: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "roles", tuple(self.roles) if self.roles else ())
        object.__setattr__(self, "scopes", tuple(self.scopes) if self.scopes else ())

    @property
    def is_authenticated(self) -> bool:
        """Truthful authentication check enforcing the invariant UNKNOWN != AUTHENTICATED."""
        return (
            self.authentication_state == "AUTHENTICATED"
            and self.authentication_assurance in {"LOW", "MEDIUM", "HIGH"}
        )


    @property
    def effective_original_actor(self) -> ActorReference:
        """Returns original human actor if present, otherwise immediate actor reference."""
        return self.original_actor or self.actor

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor.to_dict(),
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "environment": self.environment,
            "roles": list(self.roles),
            "scopes": list(self.scopes),
            "session_id": self.session_id,
            "provenance": self.provenance,
            "credential_mechanism": self.credential_mechanism,
            "authentication_state": self.authentication_state,
            "authentication_assurance": self.authentication_assurance,
            "trust_domain": self.trust_domain,
            "federation_provenance": dict(self.federation_provenance) if self.federation_provenance else None,
            "workload_identity": self.workload_identity,
            "original_actor": self.original_actor.to_dict() if self.original_actor else None,
            "calling_workload": self.calling_workload,
            "target_workload": self.target_workload,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_untrusted_claims(cls, data: Mapping[str, Any]) -> ActorContext:
        """Northbound boundary constructor for untrusted wire claims; strips self-asserted auth."""
        actor_raw = data.get("actor", {})
        if isinstance(actor_raw, Mapping):
            act_id = actor_raw.get("actor_id", "unauthenticated-caller")
            act_type = actor_raw.get("actor_type", "HUMAN")
            disp_name = actor_raw.get("display_name")
            email = actor_raw.get("email")
            trust_dom = actor_raw.get("trust_domain")
        else:
            act_id = "unauthenticated-caller"
            act_type = "HUMAN"
            disp_name = None
            email = None
            trust_dom = None

        actor = ActorReference(
            actor_id=act_id,
            actor_type=act_type,
            display_name=disp_name,
            email=email,
            trust_domain=trust_dom,
        )
        return cls(
            actor=actor,
            organization_id=data.get("organization_id"),
            workspace_id=data.get("workspace_id"),
            project_id=data.get("project_id"),
            environment=data.get("environment"),
            roles=tuple(data.get("roles", ())),
            scopes=tuple(data.get("scopes", ())),
            session_id=data.get("session_id"),
            provenance=data.get("provenance"),
            credential_mechanism=data.get("credential_mechanism", "SYSTEM_INTERNAL"),
            authentication_state="CLAIMED",
            authentication_assurance="NONE",
            trust_domain=data.get("trust_domain") or trust_dom,
            federation_provenance=data.get("federation_provenance"),
            workload_identity=data.get("workload_identity"),
            original_actor=None,
            calling_workload=data.get("calling_workload"),
            target_workload=data.get("target_workload"),
            issued_at=data.get("issued_at"),
            expires_at=data.get("expires_at"),
        )


    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ActorContext:
        actor_raw = data["actor"]
        actor = ActorReference.from_dict(actor_raw) if isinstance(actor_raw, Mapping) else actor_raw
        orig_raw = data.get("original_actor")
        orig_actor = ActorReference.from_dict(orig_raw) if isinstance(orig_raw, Mapping) else orig_raw

        return cls(
            actor=actor,
            organization_id=data.get("organization_id"),
            workspace_id=data.get("workspace_id"),
            project_id=data.get("project_id"),
            environment=data.get("environment"),
            roles=tuple(data.get("roles", ())),
            scopes=tuple(data.get("scopes", ())),
            session_id=data.get("session_id"),
            provenance=data.get("provenance"),
            credential_mechanism=data.get("credential_mechanism", "SYSTEM_INTERNAL"),
            authentication_state=data.get("authentication_state", "UNAUTHENTICATED"),
            authentication_assurance=data.get("authentication_assurance", "NONE"),
            trust_domain=data.get("trust_domain"),
            federation_provenance=data.get("federation_provenance"),
            workload_identity=data.get("workload_identity"),
            original_actor=orig_actor,
            calling_workload=data.get("calling_workload"),
            target_workload=data.get("target_workload"),
            issued_at=data.get("issued_at"),
            expires_at=data.get("expires_at"),
        )


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

