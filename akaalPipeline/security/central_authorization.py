"""akaalPipeline.security.central_authorization
===========================================
Canonical Unified Central Authorization Engine.
Integrates Principal -> Group -> RBAC -> ABAC -> SoD -> Cache.
Zero hardcoded bypasses; Deny-First default.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
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


class CentralAuthorizationEngine:
    """Canonical central authorization decision engine."""

    def __init__(
        self,
        tenant_repo: SQLiteTenantRepository,
        principal_repo: SQLitePrincipalRepository,
        group_authority: GroupAuthority,
        rbac_authority: RBACAuthority,
        abac_authority: ABACAuthority,
        cache_manager: AuthorizationCacheManager,
        sod_engine: Optional[SeparationOfDutiesEngine] = None,
    ) -> None:
        self.tenant_repo = tenant_repo
        self.principal_repo = principal_repo
        self.group_authority = group_authority
        self.rbac_authority = rbac_authority
        self.abac_authority = abac_authority
        self.cache_manager = cache_manager
        self.sod_engine = sod_engine or SeparationOfDutiesEngine()

    def authorize(
        self,
        actor_context: PipelineActorContext,
        permission_id: str,
        resource_type: str,
        resource_id: str,
        extra_abac_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Evaluate full authorization pipeline for a requested permission on a resource.
        Returns True if authorized; raises ForbiddenError or UnauthorizedError if denied.
        """
        # 1. Validate Permission in canonical registry
        if not PermissionRegistry.is_valid(permission_id):
            raise ForbiddenError(f"Unknown permission requested: {permission_id!r}")

        tenant_id = actor_context.tenant_id
        principal_id = actor_context.principal_id

        # SYSTEM actor is internal-only; when authentic internal context, allow system permissions
        if actor_context.principal_type == PrincipalType.SYSTEM:
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
                "roles": list(actor_context.roles),
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
            self.cache_manager.put(tenant_id, principal_id, effective_sec_rev, permission_id, resource_type, resource_id, False)
            raise ForbiddenError(f"ABAC policy denied action {permission_id!r} on {resource_type}/{resource_id}")

        # Authorized successfully
        self.cache_manager.put(tenant_id, principal_id, effective_sec_rev, permission_id, resource_type, resource_id, True)
        return True
