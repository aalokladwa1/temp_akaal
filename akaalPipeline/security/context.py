"""akaalPipeline.security.context
==============================
Canonical Pipeline Actor & Zero-Trust Security Context Model.
Adapts akaalIPC.security.ActorContext with strict zero-trust provenance preservation.

CRITICAL INVARIANTS:
1. Authentication establishes WHO the principal is. Existing P5 authorization determines WHAT the principal may do.
2. `roles`, `groups`, and `scopes` are authenticated external attributes / policy inputs, NOT direct authorization permissions.
3. SYSTEM_INTERNAL is NEVER an automatic authentication or authorization bypass.
   INTERNAL != AUTOMATICALLY_AUTHENTICATED and INTERNAL != AUTOMATICALLY_AUTHORIZED.
4. UNKNOWN_AUTHENTICATION != AUTHENTICATED.
5. Missing identity != Administrator. Missing tenant != Global tenant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from akaalIPC.security.context import (
    ActorContext as IPCActorContext,
    ActorReference as IPCActorReference,
)
from akaalPipeline.contracts.enums import (
    AuthenticationAssurance,
    AuthenticationState,
    CredentialMechanism,
    PrincipalType,
)


@dataclass(frozen=True)
class PipelineActorContext:
    """Canonical Zero-Trust Security Context for pipeline execution and context propagation."""

    actor_id: str
    actor_type: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    organization_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    environment: Optional[str] = None
    roles: Tuple[str, ...] = field(default_factory=tuple)
    scopes: Tuple[str, ...] = field(default_factory=tuple)
    session_id: Optional[str] = None
    provenance: Optional[str] = None

    # Zero-Trust P7 Canonical Dimensions (Decoupled & Provenance-Preserving)
    credential_mechanism: Union[CredentialMechanism, str] = CredentialMechanism.SYSTEM_INTERNAL
    authentication_state: Union[AuthenticationState, str] = AuthenticationState.UNAUTHENTICATED
    authentication_assurance: Union[AuthenticationAssurance, str] = AuthenticationAssurance.NONE
    trust_domain: Optional[str] = None
    federation_provenance: Optional[Dict[str, Any]] = None
    workload_identity: Optional[str] = None
    original_actor: Optional[Union[PipelineActorContext, IPCActorReference, Dict[str, Any]]] = None
    calling_workload: Optional[str] = None
    target_workload: Optional[str] = None
    issued_at: Optional[str] = None
    expires_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.actor_id or not str(self.actor_id).strip():
            raise ValueError("PipelineActorContext.actor_id cannot be empty")
        if not self.actor_type or not str(self.actor_type).strip():
            raise ValueError("PipelineActorContext.actor_type cannot be empty")

        object.__setattr__(self, "roles", tuple(self.roles) if self.roles else ())
        object.__setattr__(self, "scopes", tuple(self.scopes) if self.scopes else ())

        # Normalize enum values to string representation for deterministic serialization
        mech = self.credential_mechanism.value if hasattr(self.credential_mechanism, "value") else str(self.credential_mechanism)
        state = self.authentication_state.value if hasattr(self.authentication_state, "value") else str(self.authentication_state)
        assurance = self.authentication_assurance.value if hasattr(self.authentication_assurance, "value") else str(self.authentication_assurance)

        object.__setattr__(self, "credential_mechanism", mech)
        object.__setattr__(self, "authentication_state", state)
        object.__setattr__(self, "authentication_assurance", assurance)

    @property
    def tenant_id(self) -> str:
        """
        Tenant identifier scope. Substitutes the fixed literal "default-tenant" when
        organization_id is omitted or empty -- this is a coalesce, NOT a fail-closed
        rejection (contrary to earlier wording here). "default-tenant" carries no
        special privilege anywhere in this codebase: it is an ordinary tenant_id
        string subject to the exact same ACTIVE-tenant + ACTIVE-principal + RBAC
        grant checks as any other tenant (see CentralAuthorizationEngine._authorize_internal).
        It cannot itself establish membership or grant authorization -- a caller still
        needs a real, pre-provisioned, active principal record under that literal
        tenant_id for any permission check to succeed. This exact behavior is a
        frozen, hostile-tested Campaign A contract (see
        tests/security/test_p71_canonical_security_foundation.py::
        test_p71_10_tenant_isolation_and_tampering, "Missing organization_id
        defaults to 'default-tenant', never a global all-access tenant") and must
        not be silently changed to a raise without a fresh owner authorization,
        since call sites throughout akaalPipeline/operations and
        akaalPipeline/application rely on this exact coalescing default for
        single-tenant/un-scoped internal query paths.
        """
        return self.organization_id or "default-tenant"

    @property
    def principal_id(self) -> str:
        return self.actor_id

    @property
    def principal_type(self) -> str:
        return self.actor_type

    def enforce_resource_scope(
        self,
        *,
        resource_tenant_id: Optional[str],
        resource_workspace_id: Optional[str] = None,
        resource_project_id: Optional[str] = None,
        resource_kind: str = "resource",
        resource_id: str = "",
    ) -> None:
        """
        Canonical P7.10 tenant/workspace/project isolation enforcement.

        Knowing a resource identifier is never proof of membership: a caller
        authenticated in one tenant must never be able to read or mutate a
        resource that belongs to a different tenant/workspace/project merely
        by supplying that resource's identifier. This is the single reusable
        enforcement point for that check -- callers must not hand-roll their
        own tenant-comparison logic (see akaalPipeline/application/query_service.py
        and akaalPipeline/application/command_handlers.py).

        Fails closed: raises `akaalPipeline.contracts.errors.PipelineError`
        (TENANT_BOUNDARY_VIOLATION) on any mismatch, including when the resource
        carries no tenant_id at all but this actor does (a resource without an
        owning tenant is never implicitly "shared").

        P7.13 item 7: TENANT_BOUNDARY_VIOLATION (not POLICY_DENIED) is used
        deliberately -- PipelineError.to_ipc_error() maps it to the same
        externally observable category+code+message as a genuine "resource does
        not exist" (NOT_FOUND), so an unauthorized caller cannot use the error
        response to learn whether a resource exists in another tenant versus not
        existing at all. The precise reason (this exception's own .code/.message)
        remains available to any in-process/internal caller, e.g. audit/evidence
        recording, that receives the exception directly.
        """
        from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode

        if resource_tenant_id != self.organization_id:
            raise PipelineError(
                PipelineErrorCode.TENANT_BOUNDARY_VIOLATION,
                f"{resource_kind} {resource_id!r} not found or unauthorized for tenant.",
            )
        if self.workspace_id and resource_workspace_id and resource_workspace_id != self.workspace_id:
            raise PipelineError(
                PipelineErrorCode.TENANT_BOUNDARY_VIOLATION,
                f"{resource_kind} {resource_id!r} belongs to a different workspace.",
            )
        if self.project_id and resource_project_id and resource_project_id != self.project_id:
            raise PipelineError(
                PipelineErrorCode.TENANT_BOUNDARY_VIOLATION,
                f"{resource_kind} {resource_id!r} belongs to a different project.",
            )

    @property
    def is_authenticated(self) -> bool:
        """
        Truthful authentication evaluation.
        Permanent Invariant: UNKNOWN_AUTHENTICATION != AUTHENTICATED.
        Process locality (SYSTEM_INTERNAL) does not automatically confer authenticated status.
        Requires explicit AUTHENTICATED state and a valid established non-NONE assurance level.
        """
        return (
            self.authentication_state == AuthenticationState.AUTHENTICATED.value
            and self.authentication_assurance in {
                AuthenticationAssurance.LOW.value,
                AuthenticationAssurance.MEDIUM.value,
                AuthenticationAssurance.HIGH.value,
            }
        )


    @property
    def effective_original_actor(self) -> Dict[str, Any]:
        """Returns provenance dictionary of original actor (e.g. human Alice) or self."""
        if self.original_actor:
            if isinstance(self.original_actor, PipelineActorContext):
                return {
                    "actor_id": self.original_actor.actor_id,
                    "actor_type": self.original_actor.actor_type,
                    "display_name": self.original_actor.display_name,
                    "email": self.original_actor.email,
                }
            if isinstance(self.original_actor, IPCActorReference):
                return {
                    "actor_id": self.original_actor.actor_id,
                    "actor_type": self.original_actor.actor_type,
                    "display_name": self.original_actor.display_name,
                    "email": self.original_actor.email,
                }
            if isinstance(self.original_actor, dict):
                return self.original_actor
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "display_name": self.display_name,
            "email": self.email,
        }

    def validate_invariants(self) -> None:
        """Enforces mandatory P7.1 fail-closed security invariants."""
        if not self.actor_id or not str(self.actor_id).strip():
            raise ValueError("FAIL_CLOSED: Missing principal identity (actor_id)")
        if not self.actor_type or not str(self.actor_type).strip():
            raise ValueError("FAIL_CLOSED: Missing principal type (actor_type)")
        if self.authentication_state not in [e.value for e in AuthenticationState]:
            raise ValueError(f"FAIL_CLOSED: Invalid authentication state {self.authentication_state!r}")
        if self.authentication_assurance not in [e.value for e in AuthenticationAssurance]:
            raise ValueError(f"FAIL_CLOSED: Invalid authentication assurance {self.authentication_assurance!r}")
        if self.credential_mechanism not in [e.value for e in CredentialMechanism]:
            raise ValueError(f"FAIL_CLOSED: Invalid credential mechanism {self.credential_mechanism!r}")
        if self.authentication_state == AuthenticationState.AUTHENTICATED.value:
            if self.authentication_assurance == AuthenticationAssurance.NONE.value:
                raise ValueError("FAIL_CLOSED: AUTHENTICATED state cannot have assurance NONE")

    def to_ipc(self) -> IPCActorContext:
        """Lossless transformation to transport-neutral akaalIPC.security.ActorContext."""
        orig_ref = None
        if self.original_actor:
            if isinstance(self.original_actor, IPCActorReference):
                orig_ref = self.original_actor
            elif isinstance(self.original_actor, PipelineActorContext):
                orig_ref = IPCActorReference(
                    actor_id=self.original_actor.actor_id,
                    actor_type=self.original_actor.actor_type,
                    display_name=self.original_actor.display_name,
                    email=self.original_actor.email,
                    trust_domain=self.original_actor.trust_domain,
                )
            elif isinstance(self.original_actor, dict):
                orig_ref = IPCActorReference(
                    actor_id=self.original_actor["actor_id"],
                    actor_type=self.original_actor["actor_type"],
                    display_name=self.original_actor.get("display_name"),
                    email=self.original_actor.get("email"),
                    trust_domain=self.original_actor.get("trust_domain"),
                )

        return IPCActorContext(
            actor=IPCActorReference(
                actor_id=self.actor_id,
                actor_type=self.actor_type,
                display_name=self.display_name,
                email=self.email,
                trust_domain=self.trust_domain,
            ),
            organization_id=self.organization_id,
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            environment=self.environment,
            roles=self.roles,
            scopes=self.scopes,
            session_id=self.session_id,
            provenance=self.provenance,
            credential_mechanism=self.credential_mechanism,
            authentication_state=self.authentication_state,
            authentication_assurance=self.authentication_assurance,
            trust_domain=self.trust_domain,
            federation_provenance=self.federation_provenance,
            workload_identity=self.workload_identity,
            original_actor=orig_ref,
            calling_workload=self.calling_workload,
            target_workload=self.target_workload,
            issued_at=self.issued_at,
            expires_at=self.expires_at,
        )

    @classmethod
    def from_ipc(cls, ipc_actor: IPCActorContext, *, trusted_boundary: bool = True) -> PipelineActorContext:
        """Lossless construction from akaalIPC.security.ActorContext."""
        ref = ipc_actor.actor
        orig_actor = None
        if ipc_actor.original_actor:
            orig_actor = {
                "actor_id": ipc_actor.original_actor.actor_id,
                "actor_type": ipc_actor.original_actor.actor_type,
                "display_name": ipc_actor.original_actor.display_name,
                "email": ipc_actor.original_actor.email,
                "trust_domain": ipc_actor.original_actor.trust_domain,
            }

        auth_state = getattr(ipc_actor, "authentication_state", "UNAUTHENTICATED")
        auth_assurance = getattr(ipc_actor, "authentication_assurance", "NONE")
        if not trusted_boundary:
            # Strip untrusted self-asserted authentication across untrusted boundaries
            auth_state = AuthenticationState.CLAIMED.value
            auth_assurance = AuthenticationAssurance.NONE.value

        return cls(
            actor_id=ref.actor_id,
            actor_type=ref.actor_type,
            display_name=ref.display_name,
            email=ref.email,
            organization_id=ipc_actor.organization_id,
            workspace_id=ipc_actor.workspace_id,
            project_id=ipc_actor.project_id,
            environment=ipc_actor.environment,
            roles=ipc_actor.roles,
            scopes=ipc_actor.scopes,
            session_id=ipc_actor.session_id,
            provenance=ipc_actor.provenance,
            credential_mechanism=getattr(ipc_actor, "credential_mechanism", "SYSTEM_INTERNAL"),
            authentication_state=auth_state,
            authentication_assurance=auth_assurance,
            trust_domain=getattr(ipc_actor, "trust_domain", ref.trust_domain),
            federation_provenance=getattr(ipc_actor, "federation_provenance", None),
            workload_identity=getattr(ipc_actor, "workload_identity", None),
            original_actor=orig_actor,
            calling_workload=getattr(ipc_actor, "calling_workload", None),
            target_workload=getattr(ipc_actor, "target_workload", None),
            issued_at=getattr(ipc_actor, "issued_at", None),
            expires_at=getattr(ipc_actor, "expires_at", None),
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe serialization preserving all zero-trust provenance fields."""
        orig_dict = None
        if self.original_actor:
            if hasattr(self.original_actor, "to_dict"):
                orig_dict = self.original_actor.to_dict()
            elif isinstance(self.original_actor, dict):
                orig_dict = self.original_actor

        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "display_name": self.display_name,
            "email": self.email,
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
            "original_actor": orig_dict,
            "calling_workload": self.calling_workload,
            "target_workload": self.target_workload,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_untrusted_claims(
        cls,
        data: Mapping[str, Any],
        *,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
    ) -> PipelineActorContext:
        """
        Northbound security boundary constructor for untrusted wire / caller claims.
        Enforces the fundamental Zero-Trust Invariant: DESERIALIZATION != AUTHENTICATION.

        Any self-asserted 'AUTHENTICATED' state or elevated assurance from untrusted wire
        is stripped and downgraded to CLAIMED / NONE until verified by an authoritative authenticator.
        """
        if "actor" in data and isinstance(data["actor"], Mapping):
            actor_data = data["actor"]
            act_id = actor_id or actor_data.get("actor_id", "unauthenticated-caller")
            act_type = actor_type or actor_data.get("actor_type", PrincipalType.HUMAN.value)
            display_name = data.get("display_name") or actor_data.get("display_name")
            email = data.get("email") or actor_data.get("email")
            trust_domain = data.get("trust_domain") or actor_data.get("trust_domain")
        else:
            act_id = actor_id or data.get("actor_id", "unauthenticated-caller")
            act_type = actor_type or data.get("actor_type", PrincipalType.HUMAN.value)
            display_name = data.get("display_name")
            email = data.get("email")
            trust_domain = data.get("trust_domain")

        return cls(
            actor_id=act_id,
            actor_type=act_type,
            display_name=display_name,
            email=email,
            organization_id=data.get("organization_id"),
            workspace_id=data.get("workspace_id"),
            project_id=data.get("project_id"),
            environment=data.get("environment"),
            roles=tuple(data.get("roles", ())),
            scopes=tuple(data.get("scopes", ())),
            session_id=data.get("session_id"),
            provenance=data.get("provenance"),
            credential_mechanism=data.get("credential_mechanism", CredentialMechanism.SYSTEM_INTERNAL.value),
            authentication_state=AuthenticationState.CLAIMED.value,
            authentication_assurance=AuthenticationAssurance.NONE.value,
            trust_domain=trust_domain,
            federation_provenance=data.get("federation_provenance"),
            workload_identity=data.get("workload_identity"),
            original_actor=data.get("original_actor"),
            calling_workload=data.get("calling_workload"),
            target_workload=data.get("target_workload"),
            issued_at=data.get("issued_at"),
            expires_at=data.get("expires_at"),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, trusted_source: bool = True) -> PipelineActorContext:
        """JSON-safe deserialization with fail-closed validation supporting both pipeline and IPC formats."""
        if not trusted_source:
            return cls.from_untrusted_claims(data)

        if "actor" in data and isinstance(data["actor"], Mapping):
            actor_data = data["actor"]
            actor_id = actor_data["actor_id"]
            actor_type = actor_data["actor_type"]
            display_name = data.get("display_name") or actor_data.get("display_name")
            email = data.get("email") or actor_data.get("email")
            trust_domain = data.get("trust_domain") or actor_data.get("trust_domain")
        else:
            actor_id = data["actor_id"]
            actor_type = data["actor_type"]
            display_name = data.get("display_name")
            email = data.get("email")
            trust_domain = data.get("trust_domain")

        return cls(
            actor_id=actor_id,
            actor_type=actor_type,
            display_name=display_name,
            email=email,
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
            trust_domain=trust_domain,
            federation_provenance=data.get("federation_provenance"),
            workload_identity=data.get("workload_identity"),
            original_actor=data.get("original_actor"),
            calling_workload=data.get("calling_workload"),
            target_workload=data.get("target_workload"),
            issued_at=data.get("issued_at"),
            expires_at=data.get("expires_at"),
        )



