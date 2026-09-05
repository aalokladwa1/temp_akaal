"""akaalPipeline.security.jit
==========================
Canonical Just-in-Time (JIT) Privilege Authority.
Manages time-bound, scoped, governor-approved temporary role grants.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import GrantResourceType, GrantSubjectType
from akaalPipeline.contracts.errors import ForbiddenError, NotFoundError, UnauthorizedError
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.state.repositories import (
    SQLitePrincipalRepository,
    SQLiteRoleGrantRepository,
    SQLiteRoleRepository,
    SQLiteTenantRepository,
)


class JITPrivilegeAuthority:
    """Canonical lifecycle authority for Just-in-Time privilege grants."""

    def __init__(
        self,
        tenant_repo: SQLiteTenantRepository,
        principal_repo: SQLitePrincipalRepository,
        role_repo: SQLiteRoleRepository,
        grant_repo: SQLiteRoleGrantRepository,
        config: Optional[SecurityBaselineConfig] = None,
        central_authz: Optional[Any] = None,
    ) -> None:
        self.tenant_repo = tenant_repo
        self.principal_repo = principal_repo
        self.role_repo = role_repo
        self.grant_repo = grant_repo
        self.config = config or SecurityBaselineConfig()
        # P7.12 composition-root closure: no caller anywhere in akaalIPC/akaalPipeline/
        # akaalEngine constructs JITPrivilegeAuthority (grep-confirmed: it is only ever
        # built by test fixtures, each passing exactly tenant_repo/principal_repo/
        # role_repo/grant_repo -- e.g. tests/security/test_p7_campaign_b_hostile.py:95),
        # so relying on an explicitly-injected `central_authz` alone would leave the
        # governance gate permanently unwired. Mirrors the identical, already-proven
        # akaalPipeline.security.central_authorization.CentralAuthorizationEngine
        # audit_service auto-default: construct ONE real CentralAuthorizationEngine
        # (the canonical authority -- not a second/duplicate one) reusing the SAME
        # already-injected connection (role_repo.conn), unless the caller explicitly
        # overrides it (or passes `False` to explicitly disable). This does NOT change
        # when the governance check runs -- issue_jit_grant/revoke_jit_grant below still
        # only enforce it when a `granter_actor`/`revoker_actor` is explicitly supplied
        # by the caller, exactly as before; this only removes the ALSO-having-to-supply
        # `central_authz` requirement for that already-opt-in check.
        if central_authz is False:
            self._central_authz = None
        elif central_authz is not None:
            self._central_authz = central_authz
        else:
            try:
                from akaalPipeline.identity.groups import GroupAuthority
                from akaalPipeline.security.abac import ABACAuthority
                from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
                from akaalPipeline.security.rbac import RBACAuthority
                from akaalPipeline.state.repositories import (
                    SQLiteABACPolicyRepository,
                    SQLiteGroupRepository,
                    SQLiteRolePermissionRepository,
                )

                conn = role_repo.conn
                self._central_authz = CentralAuthorizationEngine(
                    tenant_repo=tenant_repo,
                    principal_repo=principal_repo,
                    group_authority=GroupAuthority(SQLiteGroupRepository(conn), principal_repo),
                    rbac_authority=RBACAuthority(role_repo, SQLiteRolePermissionRepository(conn), grant_repo),
                    abac_authority=ABACAuthority(SQLiteABACPolicyRepository(conn)),
                )
            except Exception:
                # Same fail-safe rationale as the audit_service default: if construction
                # itself fails (e.g. a test double role_repo with no real `.conn`), the
                # opt-in governance check below simply stays unavailable rather than
                # raising out of this authority's constructor.
                self._central_authz = None

    def issue_jit_grant(
        self,
        tenant_id: str,
        principal_id: str,
        role_id: str,
        resource_type: str,
        resource_id: str,
        purpose: str,
        granted_by: str,
        duration_seconds: Optional[int] = None,
        central_authz: Optional[Any] = None,
        granter_actor: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Issue a time-bound, temporary JIT privilege grant.
        Bumps principal and tenant security revision to ensure immediate cache invalidation.

        P7.12: when both `central_authz` (a CentralAuthorizationEngine) and
        `granter_actor` (the PipelineActorContext of the principal named by
        `granted_by`) are supplied, the granter must hold IDENTITY_JIT_APPROVE
        on the target role before the grant is persisted -- `granted_by` alone
        is a caller-supplied label, never proof of authority. Both parameters
        are optional and additive for backward compatibility with existing
        direct-authority callers; when omitted, issuance behavior is
        unchanged (governance is enforced by the caller's composition root,
        not invented here as a second gate).
        """
        effective_central_authz = central_authz if central_authz is not None else self._central_authz
        if effective_central_authz is not None and granter_actor is not None:
            from akaalPipeline.security.permission_registry import PermissionRegistry

            decision = effective_central_authz.authorize_protected_operation(
                granter_actor,
                permission_id=PermissionRegistry.IDENTITY_JIT_APPROVE,
                resource_type="ROLE",
                resource_id=role_id,
            )
            if not decision.allowed:
                raise ForbiddenError(
                    f"Principal {granted_by!r} is not authorized to issue JIT grants for role {role_id!r}: "
                    f"{decision.reason_code} -- {decision.reason}"
                )

        # Validate tenant and principal
        tenant = self.tenant_repo.get_tenant(tenant_id)
        if not tenant or tenant["status"] != "ACTIVE":
            raise UnauthorizedError(f"Tenant {tenant_id!r} is not active")

        principal = self.principal_repo.get_principal(tenant_id, principal_id)
        if not principal or not principal["is_active"]:
            raise UnauthorizedError(f"Principal {principal_id!r} is not active")

        # Validate role exists
        roles = self.role_repo.get_roles(tenant_id)
        role = next((r for r in roles if r["role_id"] == role_id), None)
        if not role:
            raise NotFoundError(f"Role {role_id!r} not found in tenant {tenant_id!r}")

        # Compute duration and expiration
        effective_duration = duration_seconds or self.config.jit_max_duration_seconds
        if effective_duration > self.config.jit_max_duration_seconds:
            raise ValueError(
                f"Requested JIT duration {effective_duration}s exceeds configured maximum of {self.config.jit_max_duration_seconds}s"
            )

        now = TimeAuthority.utc_now()
        expires_at = now + timedelta(seconds=effective_duration)
        grant_id = generate_secure_id("grant-jit")

        # Persist JIT grant
        self.grant_repo.grant_role(
            grant_id=grant_id,
            tenant_id=tenant_id,
            subject_type=GrantSubjectType.PRINCIPAL.value,
            subject_id=principal_id,
            role_id=role_id,
            resource_type=resource_type,
            resource_id=resource_id,
            granted_by=granted_by,
            expires_at=expires_at.isoformat(),
            is_jit=True,
            jit_purpose=purpose,
        )

        # Bump security revision to trigger real-time cache invalidation
        self.principal_repo.bump_security_revision(tenant_id, principal_id)

        return {
            "grant_id": grant_id,
            "tenant_id": tenant_id,
            "principal_id": principal_id,
            "role_id": role_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "purpose": purpose,
            "granted_by": granted_by,
            "granted_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "duration_seconds": effective_duration,
        }

    def revoke_jit_grant(
        self,
        tenant_id: str,
        grant_id: str,
        principal_id: str,
        central_authz: Optional[Any] = None,
        revoker_actor: Optional[Any] = None,
    ) -> None:
        """
        Explicitly revoke a JIT grant and advance security revision.

        P7.12: same optional/additive governance gate as `issue_jit_grant` --
        when both `central_authz` and `revoker_actor` are supplied, the
        revoker must hold IDENTITY_GRANT_REVOKE.
        """
        effective_central_authz = central_authz if central_authz is not None else self._central_authz
        if effective_central_authz is not None and revoker_actor is not None:
            from akaalPipeline.security.permission_registry import PermissionRegistry

            decision = effective_central_authz.authorize_protected_operation(
                revoker_actor,
                permission_id=PermissionRegistry.IDENTITY_GRANT_REVOKE,
                resource_type="GRANT",
                resource_id=grant_id,
            )
            if not decision.allowed:
                raise ForbiddenError(
                    f"Not authorized to revoke JIT grant {grant_id!r}: {decision.reason_code} -- {decision.reason}"
                )

        self.grant_repo.revoke_grant(tenant_id, grant_id)
        self.principal_repo.bump_security_revision(tenant_id, principal_id)

    def is_grant_valid(self, tenant_id: str, grant_id: str) -> bool:
        """Check if a JIT grant is active and unexpired."""
        cur = self.grant_repo.conn.execute(
            "SELECT * FROM role_grants WHERE tenant_id = ? AND grant_id = ?",
            (tenant_id, grant_id),
        )
        row = cur.fetchone()
        if not row:
            return False
        d = dict(row)
        if d.get("is_revoked", 0):
            return False
        expires_at = d.get("expires_at")
        if expires_at and TimeAuthority.is_expired(expires_at):
            return False
        return True
