"""akaalPipeline.security.rbac
============================
Canonical Dynamic RBAC Authority with cycle-safe inheritance and resource scoping.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import GrantResourceType, GrantSubjectType
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.state.repositories import (
    SQLiteMigrationRepository,
    SQLiteProjectRepository,
    SQLiteRoleGrantRepository,
    SQLiteRolePermissionRepository,
    SQLiteRoleRepository,
    SQLiteWorkspaceRepository,
)


class CyclicRoleInheritanceError(ValueError):
    """Raised when a cycle is detected in the role inheritance graph."""
    pass


class RBACAuthority:
    """Canonical dynamic RBAC evaluator."""

    def __init__(
        self,
        role_repo: SQLiteRoleRepository,
        role_perm_repo: SQLiteRolePermissionRepository,
        role_grant_repo: SQLiteRoleGrantRepository,
        workspace_repo: Optional[SQLiteWorkspaceRepository] = None,
        project_repo: Optional[SQLiteProjectRepository] = None,
        migration_repo: Optional[SQLiteMigrationRepository] = None,
        config: Optional[SecurityBaselineConfig] = None,
    ) -> None:
        self.role_repo = role_repo
        self.role_perm_repo = role_perm_repo
        self.role_grant_repo = role_grant_repo
        self.workspace_repo = workspace_repo
        self.project_repo = project_repo
        self.migration_repo = migration_repo
        self.config = config or SecurityBaselineConfig()

    def resolve_role_hierarchy(self, tenant_id: str, role_id: str) -> Set[str]:
        """
        Traverse role inheritance starting from role_id.
        Enforces cycle detection and maximum depth limit.
        """
        visited: Set[str] = set()
        current: Optional[str] = role_id
        depth = 0

        while current is not None:
            if current in visited:
                raise CyclicRoleInheritanceError(f"Cyclic role inheritance detected at role {current!r}")
            if depth > self.config.max_role_inheritance_depth:
                raise CyclicRoleInheritanceError(f"Role inheritance depth exceeded max limit of {self.config.max_role_inheritance_depth}")

            visited.add(current)
            depth += 1

            role = self.role_repo.get_role(tenant_id, current)
            if not role or not role["is_active"]:
                break
            current = role.get("parent_role_id")

        return visited

    def resolve_permissions_for_roles(self, tenant_id: str, role_ids: Set[str]) -> Set[str]:
        """Resolve all permissions for a set of roles including inherited parent roles."""
        all_roles: Set[str] = set()
        for r_id in role_ids:
            all_roles.update(self.resolve_role_hierarchy(tenant_id, r_id))

        permissions: Set[str] = set()
        for r_id in all_roles:
            perms = self.role_perm_repo.get_role_permissions(tenant_id, r_id)
            permissions.update(perms)

        return permissions

    def _is_scope_applicable(
        self,
        tenant_id: str,
        grant_resource_type: str,
        grant_resource_id: str,
        req_resource_type: str,
        req_resource_id: str,
    ) -> bool:
        """
        Evaluate if a grant resource scope encompasses the requested resource.
        Hierarchy: SYSTEM -> ORGANIZATION -> WORKSPACE -> PROJECT -> MIGRATION
        """
        if grant_resource_type == GrantResourceType.SYSTEM.value:
            return True

        if grant_resource_type == GrantResourceType.ORGANIZATION.value:
            return grant_resource_id == tenant_id

        if grant_resource_type == req_resource_type:
            return grant_resource_id == req_resource_id

        # Hierarchical scope checks
        if grant_resource_type == GrantResourceType.WORKSPACE.value:
            if req_resource_type == GrantResourceType.PROJECT.value and self.project_repo:
                proj = self.project_repo.get_by_id(tenant_id, grant_resource_id, req_resource_id)
                return proj is not None
            if req_resource_type == GrantResourceType.MIGRATION.value and self.migration_repo:
                mig = self.migration_repo.get_by_id(req_resource_id)
                return mig is not None and mig.tenant_id == tenant_id and mig.workspace_id == grant_resource_id

        if grant_resource_type == GrantResourceType.PROJECT.value:
            if req_resource_type == GrantResourceType.MIGRATION.value and self.migration_repo:
                mig = self.migration_repo.get_by_id(req_resource_id)
                return mig is not None and mig.tenant_id == tenant_id and mig.project_id == grant_resource_id

        return False

    def get_effective_permissions(
        self,
        tenant_id: str,
        principal_id: str,
        group_ids: List[str],
        req_resource_type: str,
        req_resource_id: str,
    ) -> Set[str]:
        """
        Resolve all effective permissions for a principal and their groups under a specific resource scope.
        Enforces grant expiration and revocation.
        """
        subject_tuples: List[Tuple[str, str]] = [(GrantSubjectType.PRINCIPAL.value, principal_id)]
        for gid in group_ids:
            subject_tuples.append((GrantSubjectType.GROUP.value, gid))

        grants = self.role_grant_repo.list_active_grants_for_subjects(tenant_id, subject_tuples)
        now = TimeAuthority.utc_now()

        active_role_ids: Set[str] = set()
        for grant in grants:
            if grant["is_revoked"]:
                continue
            if TimeAuthority.is_expired(grant.get("expires_at")):
                continue

            if self._is_scope_applicable(
                tenant_id=tenant_id,
                grant_resource_type=grant["resource_type"],
                grant_resource_id=grant["resource_id"],
                req_resource_type=req_resource_type,
                req_resource_id=req_resource_id,
            ):
                active_role_ids.add(grant["role_id"])

        return self.resolve_permissions_for_roles(tenant_id, active_role_ids)

    def get_principal_roles(
        self,
        tenant_id: str,
        principal_id: str,
        group_ids: Optional[List[str]] = None,
        req_resource_type: str = "SYSTEM",
        req_resource_id: str = "root",
    ) -> Set[str]:
        """Resolve all authoritative active roles for a principal and groups from durable storage, including inherited parent roles."""
        subject_tuples: List[Tuple[str, str]] = [(GrantSubjectType.PRINCIPAL.value, principal_id)]
        if group_ids:
            for gid in group_ids:
                subject_tuples.append((GrantSubjectType.GROUP.value, gid))

        grants = self.role_grant_repo.list_active_grants_for_subjects(tenant_id, subject_tuples)
        active_role_ids: Set[str] = set()
        for grant in grants:
            if grant.get("is_revoked"):
                continue
            if TimeAuthority.is_expired(grant.get("expires_at")):
                continue

            if self._is_scope_applicable(
                tenant_id=tenant_id,
                grant_resource_type=grant["resource_type"],
                grant_resource_id=grant["resource_id"],
                req_resource_type=req_resource_type,
                req_resource_id=req_resource_id,
            ):
                active_role_ids.add(grant["role_id"])

        all_roles: Set[str] = set()
        for r_id in active_role_ids:
            all_roles.update(self.resolve_role_hierarchy(tenant_id, r_id))
        return all_roles


    def resolve_effective_permissions_for_subject(
        self,
        tenant_id: str,
        subject_type: str,
        subject_id: str,
        resource_type: str = "SYSTEM",
        resource_id: str = "root",
    ) -> Set[str]:
        """Resolve effective permissions for a single subject under a resource scope."""
        if subject_type == GrantSubjectType.PRINCIPAL.value:
            return self.get_effective_permissions(tenant_id, subject_id, [], resource_type, resource_id)
        else:
            return self.get_effective_permissions(tenant_id, "", [subject_id], resource_type, resource_id)
