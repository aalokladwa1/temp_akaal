"""tests.security.test_domain_17_to_24_abac_sod_and_authz
=====================================================
Hostile security tests for ABAC Policies, Separation of Duties (SoD), Authorization Cache, and CentralAuthorizationEngine (Domains 17-24).
"""

import pytest
from akaal.core.time_authority import TimeAuthority
from akaal.governance.sod.engine import SeparationOfDutiesEngine
from akaalPipeline.contracts.enums import PolicyEffect, PrincipalType
from akaalPipeline.contracts.errors import ForbiddenError, UnauthorizedError
from akaalPipeline.security.abac import ABACAuthority, MissingAttributeError
from akaalPipeline.security.cache import AuthorizationCacheManager
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.state.repositories import (
    SQLiteABACPolicyRepository,
    SQLiteGroupRepository,
    SQLitePrincipalRepository,
    SQLiteRoleGrantRepository,
    SQLiteRolePermissionRepository,
    SQLiteRoleRepository,
    SQLiteTenantRepository,
)
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def authz_fixture():
    uow = SQLiteUnitOfWork(db_path=":memory:")
    conn = uow.connection

    tenant_repo = SQLiteTenantRepository(conn)
    principal_repo = SQLitePrincipalRepository(conn)
    group_repo = SQLiteGroupRepository(conn)
    role_repo = SQLiteRoleRepository(conn)
    role_perm_repo = SQLiteRolePermissionRepository(conn)
    role_grant_repo = SQLiteRoleGrantRepository(conn)
    abac_repo = SQLiteABACPolicyRepository(conn)

    now_iso = TimeAuthority.utc_iso_now()
    tenant_repo.create("tenant-1", "Alpha Corp", "ACTIVE", now_iso)

    group_auth = GroupAuthority(group_repo, principal_repo)
    rbac_auth = RBACAuthority(role_repo, role_perm_repo, role_grant_repo)
    abac_auth = ABACAuthority(abac_repo)
    cache_mgr = AuthorizationCacheManager()
    sod_engine = SeparationOfDutiesEngine()

    central_engine = CentralAuthorizationEngine(
        tenant_repo=tenant_repo,
        principal_repo=principal_repo,
        group_authority=group_auth,
        rbac_authority=rbac_auth,
        abac_authority=abac_auth,
        cache_manager=cache_mgr,
        sod_engine=sod_engine,
    )

    return {
        "uow": uow,
        "tenant_repo": tenant_repo,
        "principal_repo": principal_repo,
        "role_repo": role_repo,
        "role_perm_repo": role_perm_repo,
        "role_grant_repo": role_grant_repo,
        "abac_repo": abac_repo,
        "central_engine": central_engine,
        "cache_mgr": cache_mgr,
    }


def test_abac_evaluation_deny_overrides_and_missing_attributes(authz_fixture):
    abac_repo = authz_fixture["abac_repo"]
    abac_auth = ABACAuthority(abac_repo)

    # 1. Create ALLOW policy: Allow migration.plan if environment equals 'staging'
    abac_repo.create_policy(
        policy_id="pol-allow-staging",
        tenant_id="tenant-1",
        name="Allow Staging Planning",
        effect="ALLOW",
        target_action="migration.plan",
        target_resource_type="MIGRATION",
        condition_expression={"equals": ["resource.environment", "staging"]},
        priority=100,
    )

    # Context with environment == staging -> ALLOW
    ctx_staging = {"resource": {"environment": "staging"}}
    effect = abac_auth.evaluate_policies("tenant-1", "migration.plan", "MIGRATION", ctx_staging)
    assert effect == PolicyEffect.ALLOW

    # Context with environment == prod -> DENY (No matching allow)
    ctx_prod = {"resource": {"environment": "production"}}
    effect = abac_auth.evaluate_policies("tenant-1", "migration.plan", "MIGRATION", ctx_prod)
    assert effect == PolicyEffect.DENY

    # Context with missing mandatory attribute -> fails closed to DENY
    effect = abac_auth.evaluate_policies("tenant-1", "migration.plan", "MIGRATION", {})
    assert effect == PolicyEffect.DENY

    # 2. Add high-priority DENY policy: Deny if classification equals 'CONFIDENTIAL'
    abac_repo.create_policy(
        policy_id="pol-deny-confidential",
        tenant_id="tenant-1",
        name="Deny Confidential",
        effect="DENY",
        target_action="migration.plan",
        target_resource_type="MIGRATION",
        condition_expression={"equals": ["resource.classification", "CONFIDENTIAL"]},
        priority=10,  # Evaluated first
    )

    ctx_staging_confidential = {"resource": {"environment": "staging", "classification": "CONFIDENTIAL"}}
    effect = abac_auth.evaluate_policies("tenant-1", "migration.plan", "MIGRATION", ctx_staging_confidential)
    assert effect == PolicyEffect.DENY


def test_central_authorization_zero_admin_bypass_and_deny_first(authz_fixture):
    principal_repo = authz_fixture["principal_repo"]
    role_repo = authz_fixture["role_repo"]
    role_perm_repo = authz_fixture["role_perm_repo"]
    role_grant_repo = authz_fixture["role_grant_repo"]
    central_engine = authz_fixture["central_engine"]

    now_iso = TimeAuthority.utc_iso_now()

    # Create user "fake-admin" who claims role "admin"
    principal_repo.create("tenant-1", "usr-fake-admin", PrincipalType.HUMAN.value, "fake-admin", created_at=now_iso)

    # Actor context asserting roles=("admin",) without actual DB grant
    actor_context = PipelineActorContext(
        actor_id="usr-fake-admin",
        actor_type="HUMAN",
        organization_id="tenant-1",
        roles=("admin", "superadmin"),
    )

    # Must FAIL with ForbiddenError (No magical admin bypass!)
    with pytest.raises(ForbiddenError, match="lacks required permission"):
        central_engine.authorize(
            actor_context=actor_context,
            permission_id="migration.execute",
            resource_type="ORGANIZATION",
            resource_id="tenant-1",
        )

    # Grant proper DB role with permission
    role_repo.create_role("rol-executor", "tenant-1", "MigrationExecutor")
    role_perm_repo.add_permission("tenant-1", "rol-executor", "migration.execute")
    role_grant_repo.create_grant(
        grant_id="grt-exec-1",
        tenant_id="tenant-1",
        subject_type="PRINCIPAL",
        subject_id="usr-fake-admin",
        role_id="rol-executor",
        resource_type="ORGANIZATION",
        resource_id="tenant-1",
        granted_by="usr-fake-admin",
        granted_at=now_iso,
    )
    principal_repo.bump_security_revision("tenant-1", "usr-fake-admin", now_iso)

    # Now authorization SUCCEEDS
    assert central_engine.authorize(
        actor_context=actor_context,
        permission_id="migration.execute",
        resource_type="ORGANIZATION",
        resource_id="tenant-1",
    ) is True


def test_authorization_cache_revision_invalidation(authz_fixture):
    principal_repo = authz_fixture["principal_repo"]
    role_repo = authz_fixture["role_repo"]
    role_perm_repo = authz_fixture["role_perm_repo"]
    role_grant_repo = authz_fixture["role_grant_repo"]
    central_engine = authz_fixture["central_engine"]
    cache_mgr = authz_fixture["cache_mgr"]

    now_iso = TimeAuthority.utc_iso_now()
    principal_repo.create("tenant-1", "usr-dave", PrincipalType.HUMAN.value, "dave", created_at=now_iso)
    role_repo.create_role("rol-reader", "tenant-1", "Reader")
    role_perm_repo.add_permission("tenant-1", "rol-reader", "migration.read")
    role_grant_repo.create_grant(
        grant_id="grt-read-1",
        tenant_id="tenant-1",
        subject_type="PRINCIPAL",
        subject_id="usr-dave",
        role_id="rol-reader",
        resource_type="ORGANIZATION",
        resource_id="tenant-1",
        granted_by="usr-dave",
        granted_at=now_iso,
    )

    actor_ctx = PipelineActorContext(
        actor_id="usr-dave",
        actor_type="HUMAN",
        organization_id="tenant-1",
    )

    # Initial check populates cache
    assert central_engine.authorize(actor_ctx, "migration.read", "ORGANIZATION", "tenant-1") is True

    # Revoking grant and bumping security revision immediately invalidates cache
    role_grant_repo.revoke_grant("tenant-1", "grt-read-1", now_iso)
    principal_repo.bump_security_revision("tenant-1", "usr-dave", now_iso)

    # Next call immediately DENIES (no stale cached allow)
    with pytest.raises(ForbiddenError):
        central_engine.authorize(actor_ctx, "migration.read", "ORGANIZATION", "tenant-1")
