"""akaalPipeline.identity.groups
==============================
Canonical Flat Group Authority.
In P5.9, groups are strictly flat single-level collections of tenant principals.
Nested groups are prohibited and fail closed.
"""

from __future__ import annotations

from typing import List, Optional
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.state.repositories import (
    SQLiteGroupRepository,
    SQLitePrincipalRepository,
)


class NestedGroupsNotSupportedError(ValueError):
    """Raised when group nesting is attempted in P5.9."""
    pass


class GroupAuthority:
    """Canonical authority managing flat single-level enterprise groups."""

    def __init__(
        self,
        group_repo: SQLiteGroupRepository,
        principal_repo: SQLitePrincipalRepository,
    ) -> None:
        self.group_repo = group_repo
        self.principal_repo = principal_repo

    def create_group(
        self,
        tenant_id: str,
        name: str,
        description: str = "",
    ) -> str:
        """Create a tenant-scoped flat group."""
        if not tenant_id or not name:
            raise ValueError("tenant_id and name are required")

        group_id = generate_secure_id("grp")
        now_iso = TimeAuthority.utc_iso_now()
        self.group_repo.create_group(group_id, tenant_id, name, description, now_iso)
        return group_id

    def add_member(
        self,
        tenant_id: str,
        group_id: str,
        principal_id: str,
        granted_by: str,
    ) -> None:
        """Add a principal to a flat group. Prohibits nested groups."""
        # Check if principal exists
        principal = self.principal_repo.get_by_id(tenant_id, principal_id)
        if not principal:
            # Check if principal_id is another group (nested group attempt)
            if principal_id.startswith("grp-"):
                raise NestedGroupsNotSupportedError("Nested groups are unsupported in P5.9")
            raise ValueError(f"Principal {principal_id!r} not found in tenant {tenant_id!r}")

        now_iso = TimeAuthority.utc_iso_now()
        self.group_repo.add_member(tenant_id, group_id, principal_id, granted_by, now_iso)
        self.principal_repo.bump_security_revision(tenant_id, principal_id, now_iso)

    def remove_member(
        self,
        tenant_id: str,
        group_id: str,
        principal_id: str,
    ) -> None:
        """Remove a principal from a flat group."""
        self.group_repo.remove_member(tenant_id, group_id, principal_id)
        now_iso = TimeAuthority.utc_iso_now()
        self.principal_repo.bump_security_revision(tenant_id, principal_id, now_iso)

    def get_principal_groups(self, tenant_id: str, principal_id: str) -> List[str]:
        """Get all flat group IDs to which a principal belongs."""
        return self.group_repo.get_principal_groups(tenant_id, principal_id)
