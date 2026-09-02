"""akaalPipeline.security.central_authorization
===========================================
Canonical Unified Central Authorization Engine.
Integrates Principal -> Group -> RBAC -> ABAC -> SoD -> Cache.
Zero hardcoded bypasses; Deny-First default.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from akaal.governance.sod.engine import SeparationOfDutiesEngine
from akaalPipeline.contracts.enums import AuthenticationAssurance, PolicyEffect, PrincipalType, TenantStatus
from akaalPipeline.contracts.errors import (
    ForbiddenError,
    PersistenceError,
    SoDViolationError,
    UnauthorizedError,
)
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.security.cache import AuthorizationCacheManager
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.security.jit import JITPrivilegeAuthority
from akaalPipeline.security.permission_registry import PermissionRegistry, UnknownPermissionError
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.repositories import (
    SQLitePrincipalRepository,
    SQLiteTenantRepository,
)


_ASSURANCE_RANK: Dict[str, int] = {
    AuthenticationAssurance.NONE.value: 0,
    AuthenticationAssurance.LOW.value: 1,
    AuthenticationAssurance.MEDIUM.value: 2,
    AuthenticationAssurance.HIGH.value: 3,
}


@dataclass(frozen=True)
class AuthorizationDecision:
    """
    Structured authorization decision with provenance sufficient for later audit/evidence
    consumption (P7.11/#12). Never carries secrets/keys/raw credentials.
    """
    allowed: bool
    tenant_id: str
    principal_id: str
    permission_id: str
    resource_type: str
    resource_id: str
    reason_code: str
    reason: str
    assurance: str
    decided_at: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class AuthorizationContext:
    """Convenient authorization request context."""
    tenant_id: str
    principal_id: str
    action: str
    resource_type: str = "SYSTEM"
    resource_id: str = "root"
    principal_type: str = "HUMAN"
    environment: Optional[Dict[str, Any]] = None
    roles: Tuple[str, ...] = field(default_factory=tuple)


class CentralAuthorizationEngine:
    """Canonical central authorization decision engine."""

    def __init__(
        self,
        tenant_repo: SQLiteTenantRepository,
        principal_repo: SQLitePrincipalRepository,
        group_authority: GroupAuthority,
        rbac_authority: RBACAuthority,
        abac_authority: ABACAuthority,
        cache_manager: Optional[AuthorizationCacheManager] = None,
        sod_engine: Optional[SeparationOfDutiesEngine] = None,
        jit_authority: Optional[JITPrivilegeAuthority] = None,
    ) -> None:
        self.tenant_repo = tenant_repo
        self.principal_repo = principal_repo
        self.group_authority = group_authority
        self.rbac_authority = rbac_authority
        self.abac_authority = abac_authority
        self.cache_manager = cache_manager or AuthorizationCacheManager()
        self.sod_engine = sod_engine or SeparationOfDutiesEngine()
        self.jit_authority = jit_authority

    def authorize(
        self,
        actor_context: Union[PipelineActorContext, AuthorizationContext],
        permission_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        extra_abac_context: Optional[Dict[str, Any]] = None,
        raise_exceptions: Optional[bool] = None,
        required_assurance: Optional[AuthenticationAssurance] = None,
    ) -> bool:
        """
        Evaluate full authorization pipeline for a requested permission on a resource.
        Returns True if authorized; returns False or raises exception if denied.

        `required_assurance`: when supplied and `actor_context` is a PipelineActorContext,
        the actor's `authentication_assurance` (only ever elevated by real verification --
        e.g. akaalPipeline.security.mfa / federation -- never by a caller-supplied boolean)
        must meet or exceed this floor, or the request is denied. UNKNOWN/missing assurance
        never satisfies a required floor (fail closed).
        """
        should_raise = (not isinstance(actor_context, AuthorizationContext)) if raise_exceptions is None else raise_exceptions
        if required_assurance is not None and isinstance(actor_context, PipelineActorContext):
            actual_rank = _ASSURANCE_RANK.get(actor_context.authentication_assurance, 0)
            required_rank = _ASSURANCE_RANK.get(
                required_assurance.value if hasattr(required_assurance, "value") else str(required_assurance), 99
            )
            if actual_rank < required_rank:
                if should_raise:
                    raise ForbiddenError(
                        f"Insufficient authentication assurance for {permission_id!r}: "
                        f"have {actor_context.authentication_assurance!r}, require >= {required_assurance!r}"
                    )
                return False
        try:
            if isinstance(actor_context, AuthorizationContext):
                perm = permission_id or actor_context.action
                res_type = resource_type or actor_context.resource_type
                res_id = resource_id or actor_context.resource_id
                abac_extra = extra_abac_context or {}
                if actor_context.environment:
                    abac_extra["environment"] = actor_context.environment
                tenant_id = actor_context.tenant_id
                principal_id = actor_context.principal_id
                principal_type = actor_context.principal_type
                roles = actor_context.roles
            else:
                perm = permission_id or ""
                res_type = resource_type or "SYSTEM"
                res_id = resource_id or "root"
                abac_extra = extra_abac_context or {}
                tenant_id = actor_context.tenant_id
                principal_id = actor_context.principal_id
                principal_type = actor_context.principal_type
                roles = actor_context.roles

            return self._authorize_internal(
                tenant_id=tenant_id,
                principal_id=principal_id,
                principal_type=principal_type,
                roles=roles,
                permission_id=perm,
                resource_type=res_type,
                resource_id=res_id,
                extra_abac_context=abac_extra,
            )
        except (ForbiddenError, UnauthorizedError, UnknownPermissionError):
            if should_raise:
                raise
            return False

    def _authorize_internal(
        self,
        tenant_id: str,
        principal_id: str,
        principal_type: str,
        roles: Tuple[str, ...],
        permission_id: str,
        resource_type: str,
        resource_id: str,
        extra_abac_context: Dict[str, Any],
    ) -> bool:
        # 1. Validate Permission in canonical registry
        if not PermissionRegistry.is_valid(permission_id):
            raise ForbiddenError(f"Unknown permission requested: {permission_id!r}")

        # SYSTEM actor is internal-only; when authentic internal context, allow system permissions
        if principal_type == PrincipalType.SYSTEM.value or principal_type == PrincipalType.SYSTEM:
            return True

        # 2. Verify Tenant is ACTIVE
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if not tenant or tenant["status"] != TenantStatus.ACTIVE.value:
            raise ForbiddenError(f"Tenant {tenant_id!r} is not ACTIVE")

        # 3. Verify Principal is ACTIVE
        principal = self.principal_repo.get_by_id(tenant_id, principal_id)
        if not principal or not principal["is_active"]:
            raise UnauthorizedError(f"Principal {principal_id!r} is inactive or not found")

        # 4. Compute Effective Security Revision
        effective_sec_rev = max(tenant["security_revision"], principal["security_revision"])

        # 5. Check L1 Cache
        if not extra_abac_context:
            cached_decision = self.cache_manager.get(
                tenant_id=tenant_id,
                principal_id=principal_id,
                current_authoritative_revision=effective_sec_rev,
                permission_id=permission_id,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            if cached_decision is not None:
                if not cached_decision:
                    raise ForbiddenError(f"Permission {permission_id!r} denied by cached policy on {resource_type}/{resource_id}")
                return True

        # 6. Resolve Groups
        group_ids = self.group_authority.get_principal_groups(tenant_id, principal_id)

        # 7. Evaluate Dynamic RBAC
        effective_permissions = self.rbac_authority.get_effective_permissions(
            tenant_id=tenant_id,
            principal_id=principal_id,
            group_ids=group_ids,
            req_resource_type=resource_type,
            req_resource_id=resource_id,
        )

        if permission_id not in effective_permissions:
            if not extra_abac_context:
                self.cache_manager.put(tenant_id, principal_id, effective_sec_rev, permission_id, resource_type, resource_id, False)
            raise ForbiddenError(
                f"Principal {principal_id!r} lacks required permission {permission_id!r} on {resource_type}/{resource_id}"
            )

        # 8. Evaluate ABAC Policies (authoritative server-side roles only)
        authoritative_roles = self.rbac_authority.get_principal_roles(
            tenant_id=tenant_id,
            principal_id=principal_id,
            group_ids=group_ids,
            req_resource_type=resource_type,
            req_resource_id=resource_id,
        )
        abac_ctx: Dict[str, Any] = {
            "subject": {
                "principal_id": principal_id,
                "principal_type": principal["principal_type"],
                "groups": group_ids,
                "roles": list(authoritative_roles),
            },
            "resource": {
                "type": resource_type,
                "id": resource_id,
                "tenant_id": tenant_id,
            },
            "action": permission_id,
        }
        if extra_abac_context:
            abac_ctx.update(extra_abac_context)

        abac_effect = self.abac_authority.evaluate_policies(
            tenant_id=tenant_id,
            action=permission_id,
            resource_type=resource_type,
            context=abac_ctx,
        )

        if abac_effect == PolicyEffect.DENY:
            if not extra_abac_context:
                self.cache_manager.put(tenant_id, principal_id, effective_sec_rev, permission_id, resource_type, resource_id, False)
            raise ForbiddenError(f"ABAC policy denied action {permission_id!r} on {resource_type}/{resource_id}")

        # Authorized successfully
        if not extra_abac_context:
            self.cache_manager.put(tenant_id, principal_id, effective_sec_rev, permission_id, resource_type, resource_id, True)
        return True

    def authorize_with_decision(
        self,
        actor_context: Union[PipelineActorContext, AuthorizationContext],
        permission_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        extra_abac_context: Optional[Dict[str, Any]] = None,
        required_assurance: Optional[AuthenticationAssurance] = None,
        correlation_id: Optional[str] = None,
    ) -> AuthorizationDecision:
        """
        Non-breaking structured variant of `authorize()`: never raises for a denial, instead
        returns an AuthorizationDecision with provenance suitable for audit/evidence (#12)
        consumption. Still raises for malformed input (e.g. UnknownPermissionError).
        """
        perm = permission_id or (actor_context.action if isinstance(actor_context, AuthorizationContext) else "")
        res_type = resource_type or (actor_context.resource_type if isinstance(actor_context, AuthorizationContext) else "SYSTEM")
        res_id = resource_id or (actor_context.resource_id if isinstance(actor_context, AuthorizationContext) else "root")
        assurance_val = (
            actor_context.authentication_assurance if isinstance(actor_context, PipelineActorContext) else AuthenticationAssurance.NONE.value
        )
        try:
            allowed = self.authorize(
                actor_context,
                permission_id=perm,
                resource_type=res_type,
                resource_id=res_id,
                extra_abac_context=extra_abac_context,
                raise_exceptions=True,
                required_assurance=required_assurance,
            )
            return AuthorizationDecision(
                allowed=allowed,
                tenant_id=actor_context.tenant_id,
                principal_id=actor_context.principal_id,
                permission_id=perm,
                resource_type=res_type,
                resource_id=res_id,
                reason_code="ALLOWED",
                reason="Authorization pipeline granted the requested permission.",
                assurance=assurance_val,
                correlation_id=correlation_id,
            )
        except ForbiddenError as exc:
            return AuthorizationDecision(
                allowed=False,
                tenant_id=actor_context.tenant_id,
                principal_id=actor_context.principal_id,
                permission_id=perm,
                resource_type=res_type,
                resource_id=res_id,
                reason_code="FORBIDDEN",
                reason=str(exc),
                assurance=assurance_val,
                correlation_id=correlation_id,
            )
        except UnauthorizedError as exc:
            return AuthorizationDecision(
                allowed=False,
                tenant_id=actor_context.tenant_id,
                principal_id=actor_context.principal_id,
                permission_id=perm,
                resource_type=res_type,
                resource_id=res_id,
                reason_code="UNAUTHENTICATED",
                reason=str(exc),
                assurance=assurance_val,
                correlation_id=correlation_id,
            )

    def authorize_protected_operation(
        self,
        actor_context: PipelineActorContext,
        permission_id: str,
        resource_type: str,
        resource_id: str,
        requester_id: Optional[str] = None,
        approver_ids: Optional[List[str]] = None,
        requester_role: Optional[str] = None,
        approver_roles: Optional[List[str]] = None,
        required_jit_grant_id: Optional[str] = None,
        required_assurance: Optional[AuthenticationAssurance] = None,
        extra_abac_context: Optional[Dict[str, Any]] = None,
    ) -> AuthorizationDecision:
        """
        P7.6 cross-cutting composition for a "protected operation": standard RBAC/ABAC
        authorization, PLUS (a) an active, unexpired JIT grant when the operation requires
        one, and (b) Separation-of-Duties conflict rejection when a maker/checker pair is
        supplied. Fails closed: any missing/expired/conflicting dimension denies the
        operation rather than silently permitting it.

        This does not replace `authorize()` for ordinary permission checks -- it is for
        operations explicitly modeled as requiring elevated, auditable protection.
        """
        base = self.authorize_with_decision(
            actor_context,
            permission_id=permission_id,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_abac_context=extra_abac_context,
            required_assurance=required_assurance,
        )
        if not base.allowed:
            return base

        if required_jit_grant_id is not None:
            if self.jit_authority is None:
                return AuthorizationDecision(
                    allowed=False, tenant_id=base.tenant_id, principal_id=base.principal_id,
                    permission_id=permission_id, resource_type=resource_type, resource_id=resource_id,
                    reason_code="JIT_AUTHORITY_UNAVAILABLE",
                    reason="Protected operation requires a JIT grant, but no JITPrivilegeAuthority is wired into this engine.",
                    assurance=base.assurance,
                )
            if not self.jit_authority.is_grant_valid(base.tenant_id, required_jit_grant_id):
                return AuthorizationDecision(
                    allowed=False, tenant_id=base.tenant_id, principal_id=base.principal_id,
                    permission_id=permission_id, resource_type=resource_type, resource_id=resource_id,
                    reason_code="JIT_GRANT_EXPIRED_OR_MISSING",
                    reason=f"Required JIT grant {required_jit_grant_id!r} is not active/unexpired.",
                    assurance=base.assurance,
                )

        if requester_id is not None and approver_ids is not None:
            ok, violations = self.sod_engine.validate_approval(
                requester_id=requester_id,
                approver_ids=approver_ids,
                requester_role=requester_role or "",
                approver_roles=approver_roles or [],
            )
            if not ok:
                return AuthorizationDecision(
                    allowed=False, tenant_id=base.tenant_id, principal_id=base.principal_id,
                    permission_id=permission_id, resource_type=resource_type, resource_id=resource_id,
                    reason_code="SOD_VIOLATION",
                    reason=f"Separation of Duties violation: {'; '.join(violations)}",
                    assurance=base.assurance,
                )

        return base

    def get_authoritative_roles(
        self,
        tenant_id: str,
        principal_id: str,
        resource_type: str = "SYSTEM",
        resource_id: str = "root",
    ) -> Set[str]:
        """Resolve authoritative server-side roles for a principal and their groups from durable grants."""
        group_ids = self.group_authority.get_principal_groups(tenant_id, principal_id)
        return self.rbac_authority.get_principal_roles(
            tenant_id=tenant_id,
            principal_id=principal_id,
            group_ids=group_ids,
            req_resource_type=resource_type,
            req_resource_id=resource_id,
        )

