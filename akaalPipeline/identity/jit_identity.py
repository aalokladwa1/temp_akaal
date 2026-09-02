"""akaalPipeline.identity.jit_identity
===================================
P7.5 Just-in-Time Identity Lifecycle Authority.

Provisions/updates durable enterprise_principals rows from ALREADY-VERIFIED federated
identity (a PipelineActorContext produced by akaalPipeline.security.federation.manager
.FederationManager, i.e. one that passed real OIDC/SAML/LDAP cryptographic verification).

This module does NOT authenticate anyone. It consumes Campaign A's verified trust
provenance and deterministically maps it onto a canonical AKAAL principal, reusing the
existing SQLitePrincipalRepository / enterprise_principals authority rather than creating
a parallel identity store.

Strict invariants:
1. Only actor_context.is_authenticated == True (AUTHENTICATED state + non-NONE assurance,
   enforced by PipelineActorContext itself) may create/update an identity.
2. Provisioning is idempotent: the same (tenant_id, provider_id, external_subject) always
   maps to the same principal_id (deterministic, collision-safe scoped username).
3. A tenant/subject collision (same scoped username claimed by two different upstream
   subjects) fails closed rather than silently overwriting.
4. First login creates; repeat login only updates display metadata + provenance + bumps
   security_revision so any cached authorization decisions are invalidated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from sqlite3 import IntegrityError
from typing import Any, Dict, Optional

from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import PrincipalType, TenantStatus
from akaalPipeline.contracts.errors import ConflictError, ForbiddenError, UnauthorizedError
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.repositories import SQLitePrincipalRepository, SQLiteTenantRepository


class JITIdentityPolicyViolationError(ForbiddenError):
    """Raised when JIT identity provisioning policy rejects the request."""


@dataclass(frozen=True)
class JITIdentityPolicy:
    """
    Dynamic, configuration-driven policy governing which federated identities may be
    JIT-provisioned. No behavior here is hardcoded per-tenant/per-provider identity --
    all thresholds are policy inputs supplied by the caller/operator configuration.
    """
    allowed_provider_ids: Optional[frozenset[str]] = None  # None == no provider restriction
    require_email: bool = False
    require_tenant_active: bool = True
    default_principal_type: PrincipalType = PrincipalType.HUMAN


@dataclass(frozen=True)
class JITIdentityResult:
    principal_id: str
    tenant_id: str
    created: bool  # True on first-login provisioning, False on repeat-login update
    security_revision: int


class JITIdentityAuthority:
    """Canonical JIT identity lifecycle authority for verified federated principals."""

    def __init__(
        self,
        tenant_repo: SQLiteTenantRepository,
        principal_repo: SQLitePrincipalRepository,
        policy: Optional[JITIdentityPolicy] = None,
    ) -> None:
        self.tenant_repo = tenant_repo
        self.principal_repo = principal_repo
        self.policy = policy or JITIdentityPolicy()

    def _commit_if_owned(self, owns_transaction: bool) -> None:
        """
        C5 hostile-review fix (composability-corrected; see
        akaalPipeline.security.mfa.MFAAuthority._durability_scope for full rationale). A
        hostile test proved unconditional self-commit prematurely commits an
        externally-owned `with uow:` transaction. `owns_transaction` must be captured via
        `not self.principal_repo.conn.in_transaction` BEFORE this call's first write; only
        commit when this call itself opened the transaction.
        """
        if owns_transaction:
            self.principal_repo.conn.commit()

    @staticmethod
    def _scoped_username(actor_context: PipelineActorContext) -> str:
        """
        Deterministic collision-safe username: '<provider_id>:<external_subject>'.
        Prevents Provider A subject '123' from colliding with Provider B subject '123'.
        """
        prov = (actor_context.federation_provenance or {}).get("provider_id")
        subj = (actor_context.federation_provenance or {}).get("external_subject")
        if not prov or not subj:
            # actor_id from FederationManager._mint_canonical_context is already the
            # scoped_principal_id computed by the validator; fall back to it directly.
            return f"federated:{actor_context.actor_id}"
        return f"{prov}:{subj}"

    def provision_from_federated_context(self, actor_context: PipelineActorContext) -> JITIdentityResult:
        """
        Idempotently creates or updates a durable principal from a verified federated
        actor context. Fails closed if the context is not genuinely AUTHENTICATED, if the
        provider is not policy-allowed, or if a subject/tenant collision is detected.
        """
        if not actor_context.is_authenticated:
            raise UnauthorizedError(
                "JIT identity provisioning requires a verified AUTHENTICATED actor context; "
                f"got state={actor_context.authentication_state!r} assurance={actor_context.authentication_assurance!r}"
            )
        if not actor_context.federation_provenance:
            raise UnauthorizedError(
                "JIT identity provisioning requires federation_provenance from a verified federation flow; none present."
            )

        provider_id = actor_context.federation_provenance.get("provider_id")
        if self.policy.allowed_provider_ids is not None and provider_id not in self.policy.allowed_provider_ids:
            raise JITIdentityPolicyViolationError(
                f"Federation provider {provider_id!r} is not permitted to JIT-provision identities by current policy"
            )
        if self.policy.require_email and not actor_context.email:
            raise JITIdentityPolicyViolationError("JIT identity policy requires a verified email claim; none present")

        tenant_id = actor_context.tenant_id
        if self.policy.require_tenant_active:
            tenant = self.tenant_repo.get_by_id(tenant_id)
            if not tenant or tenant["status"] != TenantStatus.ACTIVE.value:
                raise ForbiddenError(f"Tenant {tenant_id!r} is not ACTIVE; JIT identity provisioning refused")

        scoped_username = self._scoped_username(actor_context)
        now_iso = TimeAuthority.utc_iso_now()

        # Ownership captured BEFORE any write in this call (reads above are transaction-neutral).
        owns_transaction = not self.principal_repo.conn.in_transaction

        existing = self.principal_repo.get_by_username(tenant_id, scoped_username)
        provenance_meta: Dict[str, Any] = {
            "federation_provenance": dict(actor_context.federation_provenance or {}),
            "trust_domain": actor_context.trust_domain,
            "last_authenticated_at": actor_context.issued_at,
        }

        if existing is not None:
            # Collision protection: the resolved username deterministically maps 1:1 to
            # provider+subject, so an existing row under this exact scoped username IS the
            # correct identity -- update, don't create a duplicate.
            if not existing["is_active"]:
                raise ForbiddenError(f"Principal for {scoped_username!r} exists but is deactivated; JIT re-activation requires explicit administrative action")
            self.principal_repo.update_metadata(tenant_id, existing["principal_id"], provenance_meta, updated_at=now_iso)
            new_rev = self.principal_repo.bump_security_revision(tenant_id, existing["principal_id"], updated_at=now_iso)
            self._commit_if_owned(owns_transaction)
            return JITIdentityResult(
                principal_id=existing["principal_id"], tenant_id=tenant_id, created=False, security_revision=new_rev
            )

        principal_id = generate_secure_id("jitusr")
        try:
            created = self.principal_repo.create(
                tenant_id=tenant_id,
                principal_id=principal_id,
                principal_type=self.policy.default_principal_type.value,
                username=scoped_username,
                display_name=actor_context.display_name,
                email=actor_context.email,
                metadata=provenance_meta,
                created_at=now_iso,
            )
        except IntegrityError:
            # Hostile-review (B9) finding: two genuinely concurrent first-logins for the
            # same never-before-seen federated subject can both reach this branch (neither
            # sees the other's uncommitted row) and race on create(). scoped_username is
            # deterministic for this subject, so the loser's create() fails the UNIQUE
            # constraint rather than silently duplicating -- gracefully fall back to the
            # winner's row (update, not a second identity) instead of propagating a raw
            # IntegrityError for what is, from the caller's perspective, still exactly-once
            # idempotent provisioning.
            winner = self.principal_repo.get_by_username(tenant_id, scoped_username)
            if not winner:
                raise
            self.principal_repo.update_metadata(tenant_id, winner["principal_id"], provenance_meta, updated_at=now_iso)
            new_rev = self.principal_repo.bump_security_revision(tenant_id, winner["principal_id"], updated_at=now_iso)
            self._commit_if_owned(owns_transaction)
            return JITIdentityResult(
                principal_id=winner["principal_id"], tenant_id=tenant_id, created=False, security_revision=new_rev
            )
        self._commit_if_owned(owns_transaction)
        return JITIdentityResult(
            principal_id=created["principal_id"], tenant_id=tenant_id, created=True,
            security_revision=created.get("security_revision", 1),
        )
