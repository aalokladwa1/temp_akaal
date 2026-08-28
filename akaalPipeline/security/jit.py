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
    ) -> None:
        self.tenant_repo = tenant_repo
        self.principal_repo = principal_repo
        self.role_repo = role_repo
        self.grant_repo = grant_repo
        self.config = config or SecurityBaselineConfig()

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
    ) -> Dict[str, Any]:
        """
        Issue a time-bound, temporary JIT privilege grant.
        Bumps principal and tenant security revision to ensure immediate cache invalidation.
        """
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
    ) -> None:
        """Explicitly revoke a JIT grant and advance security revision."""
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
