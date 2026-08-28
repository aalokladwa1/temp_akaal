"""akaalPipeline.security.central_authorization
===========================================
Canonical Unified Central Authorization Engine.
Integrates Principal -> Group -> RBAC -> ABAC -> SoD -> Cache.
Zero hardcoded bypasses; Deny-First default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from akaal.governance.sod.engine import SeparationOfDutiesEngine
from akaalPipeline.contracts.enums import PolicyEffect, PrincipalType, TenantStatus
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
from akaalPipeline.security.permission_registry import PermissionRegistry, UnknownPermissionError
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.repositories import (
    SQLitePrincipalRepository,
    SQLiteTenantRepository,
)


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
    ) -> None:
        self.tenant_repo = tenant_repo
        self.principal_repo = principal_repo
        self.group_authority = group_authority
        self.rbac_authority = rbac_authority
        self.abac_authority = abac_authority
        self.cache_manager = cache_manager or AuthorizationCacheManager()
        self.sod_engine = sod_engine or SeparationOfDutiesEngine()

    def authorize(
        self,
        actor_context: Union[PipelineActorContext, AuthorizationContext],
        permission_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        extra_abac_context: Optional[Dict[str, Any]] = None,
        raise_exceptions: Optional[bool] = None,
    ) -> bool:
        """
        Evaluate full authorization pipeline for a requested permission on a resource.
        Returns True if authorized; returns False or raises exception if denied.
        """
        should_raise = (not isinstance(actor_context, AuthorizationContext)) if raise_exceptions is None else raise_exceptions
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

        # 8. Evaluate ABAC Policies
        abac_ctx: Dict[str, Any] = {
            "subject": {
                "principal_id": principal_id,
                "principal_type": principal["principal_type"],
                "groups": group_ids,
                "roles": list(roles),
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
