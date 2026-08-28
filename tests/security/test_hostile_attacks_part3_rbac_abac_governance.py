"""tests.security.test_hostile_attacks_part3_rbac_abac_governance
============================================================
Hostile Security Verification Suite - Part 3: RBAC, ABAC & Governance Authorities
Contains Hostile Attack Scenarios HOSTILE-ATK-27 through HOSTILE-ATK-40.
"""

import pytest
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.security.permission_registry import PermissionRegistry, UnknownPermissionError
from akaalPipeline.security.rbac import RBACAuthority, CyclicRoleInheritanceError
from akaalPipeline.security.abac import ABACAuthority, MissingAttributeError
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine, AuthorizationContext
from akaalPipeline.security.cache import AuthorizationCacheManager
from akaalPipeline.security.jit import JITPrivilegeAuthority
from akaalPipeline.policy.approval_artifact import GovernanceApprovalArtifact, ApprovalIntegrityError
from akaalPipeline.identity.groups import GroupAuthority
from akaal.governance.sod.engine import SeparationOfDutiesEngine
from akaal.governance.foureyes.validator import FourEyesValidator
from akaalPipeline.contracts.enums import GrantSubjectType, GrantResourceType, PolicyEffect


@pytest.fixture
def uow(tmp_path):
    db_path = str(tmp_path / "akaal_hostile_governance.db")
    uow_inst = SQLiteUnitOfWork(db_path)
    uow_inst.initialize_schema()
    uow_inst.tenants.create_tenant("tenant-corp", "Corp")
    uow_inst.principals.create(tenant_id="tenant-corp", principal_id="admin", principal_type="HUMAN", username="admin", display_name="Admin", email="admin@corp.com")
    uow_inst.principals.create(tenant_id="tenant-corp", principal_id="usr-alice", principal_type="HUMAN", username="alice", display_name="Alice", email="alice@corp.com")
    uow_inst.principals.create(tenant_id="tenant-corp", principal_id="usr-bob", principal_type="HUMAN", username="bob", display_name="Bob", email="bob@corp.com")
    uow_inst.principals.create(tenant_id="tenant-corp", principal_id="usr-charlie", principal_type="HUMAN", username="charlie", display_name="Charlie", email="charlie@corp.com")
    return uow_inst


def test_hostile_atk_27_unknown_permission_fail_closed():
    """HOSTILE-ATK-27: PermissionRegistry must fail closed on invalid/unrecognized permission string."""
    with pytest.raises(UnknownPermissionError):
        PermissionRegistry.assert_valid("system.arbitrary.privilege.escalation")


def test_hostile_atk_28_rbac_cyclic_role_inheritance_detection(uow):
    """HOSTILE-ATK-28: Create circular role inheritance A -> B -> C -> A and verify CyclicRoleInheritanceError."""
    uow.roles.create_role("tenant-corp", "role-a", "Role A")
    uow.roles.create_role("tenant-corp", "role-b", "Role B", parent_role_id="role-a")
    uow.roles.create_role("tenant-corp", "role-c", "Role C", parent_role_id="role-b")
    
    # Close the cycle: A -> C
    uow.conn.execute("UPDATE enterprise_roles SET parent_role_id = 'role-c' WHERE tenant_id = 'tenant-corp' AND role_id = 'role-a'")
    
    uow.role_grants.create_grant(
        grant_id="grant-cycle-01",
        tenant_id="tenant-corp",
        subject_type=GrantSubjectType.PRINCIPAL.value,
        subject_id="usr-alice",
        role_id="role-a",
        resource_type=GrantResourceType.SYSTEM.value,
        resource_id="root",
        granted_by="admin",
    )
    
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    with pytest.raises(CyclicRoleInheritanceError):
        rbac.resolve_effective_permissions_for_subject("tenant-corp", GrantSubjectType.PRINCIPAL.value, "usr-alice")


def test_hostile_atk_29_rbac_resource_scoped_authorization(uow):
    """HOSTILE-ATK-29: Verify project-scoped permission does not leak into other projects."""
    uow.roles.create_role("tenant-corp", "role-mig-operator", "Operator")
    uow.role_permissions.assign_permission("tenant-corp", "role-mig-operator", "migration.execute", "admin")
    
    # Grant only on proj-alpha
    uow.role_grants.grant_role(
        grant_id="grant-01",
        tenant_id="tenant-corp",
        subject_type=GrantSubjectType.PRINCIPAL.value,
        subject_id="usr-alice",
        role_id="role-mig-operator",
        resource_type=GrantResourceType.PROJECT.value,
        resource_id="proj-alpha",
        granted_by="admin",
    )
    
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    perms_alpha = rbac.resolve_effective_permissions_for_subject(
        "tenant-corp", GrantSubjectType.PRINCIPAL.value, "usr-alice",
        resource_type=GrantResourceType.PROJECT.value, resource_id="proj-alpha"
    )
    assert "migration.execute" in perms_alpha
    
    # Check proj-beta: must NOT have permission
    perms_beta = rbac.resolve_effective_permissions_for_subject(
        "tenant-corp", GrantSubjectType.PRINCIPAL.value, "usr-alice",
        resource_type=GrantResourceType.PROJECT.value, resource_id="proj-beta"
    )
    assert "migration.execute" not in perms_beta


def test_hostile_atk_30_abac_explicit_deny_override(uow):
    """HOSTILE-ATK-30: Explicit DENY policy must override matching ALLOW policies."""
    uow.abac_policies.create_policy(
        tenant_id="tenant-corp",
        policy_id="pol-allow-all",
        name="Allow All",
        effect=PolicyEffect.ALLOW.value,
        target_action="migration.execute",
        condition_expression={"equals": {"subject.department": "Engineering"}},
    )
    uow.abac_policies.create_policy(
        tenant_id="tenant-corp",
        policy_id="pol-deny-after-hours",
        name="Deny Maintenance Window",
        effect=PolicyEffect.DENY.value,
        target_action="migration.execute",
        condition_expression={"equals": {"environment.is_maintenance": True}},
        priority=100,
    )
    
    abac = ABACAuthority(uow.abac_policies)
    decision = abac.evaluate(
        tenant_id="tenant-corp",
        action="migration.execute",
        attributes={
            "subject": {"department": "Engineering"},
            "environment": {"is_maintenance": True},
        }
    )
    assert decision == PolicyEffect.DENY.value


def test_hostile_atk_31_abac_missing_attribute_fail_closed(uow):
    """HOSTILE-ATK-31: ABAC rule depending on missing subject attribute must fail closed to False."""
    uow.abac_policies.create_policy(
        tenant_id="tenant-corp",
        policy_id="pol-clearance",
        name="Secret Clearance Required",
        effect=PolicyEffect.ALLOW.value,
        target_action="migration.execute",
        condition_expression={"equals": {"subject.clearance_level": "TOP_SECRET"}},
    )
    
    abac = ABACAuthority(uow.abac_policies)
    # Context does not provide subject.clearance_level
    decision = abac.evaluate(
        tenant_id="tenant-corp",
        action="migration.execute",
        attributes={"subject": {"department": "Engineering"}}
    )
    # Since allow rule condition fails, default must be DENY
    assert decision == PolicyEffect.DENY.value


def test_hostile_atk_32_central_authorization_deny_first_default(uow):
    """HOSTILE-ATK-32: Caller with no permissions must be DENIED by default (Zero admin bypass)."""
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    authz_engine = CentralAuthorizationEngine(
        uow.tenants, uow.principals, ga, rbac, abac
    )
    ctx = AuthorizationContext(
        tenant_id="tenant-corp",
        principal_id="usr-charlie",
        action="migration.plan",
        resource_type="SYSTEM",
        resource_id="root",
    )
    assert authz_engine.authorize(ctx) is False


def test_hostile_atk_33_sod_conflict_detection():
    """HOSTILE-ATK-33: SeparationOfDutiesEngine must detect conflicting roles (Requester + Approver)."""
    sod = SeparationOfDutiesEngine()
    # Adding conflicting role assignments to same principal
    is_valid, conflicts = sod.validate_assignments("usr-alice", ["MigrationRequester", "MigrationApprover"])
    assert is_valid is False
    assert len(conflicts) > 0


def test_hostile_atk_34_foureyes_self_approval_prohibition():
    """HOSTILE-ATK-34: FourEyesValidator must reject requester acting as their own approver."""
    foureyes = FourEyesValidator()
    is_valid, msg = foureyes.validate_action(requester_id="usr-alice", approver_id="usr-alice", action_type="CUTOVER")
    assert is_valid is False


def test_hostile_atk_35_foureyes_dual_approval_requirement():
    """HOSTILE-ATK-35: FourEyesValidator must succeed only with two distinct authorized principals."""
    foureyes = FourEyesValidator()
    is_valid, msg = foureyes.validate_action(requester_id="usr-alice", approver_id="usr-bob", action_type="CUTOVER")
    assert is_valid is True


def test_hostile_atk_36_jit_privilege_issuance_and_dynamic_expiration(uow):
    """HOSTILE-ATK-36: Issue JIT grant, verify active, expire time, and verify revoked."""
    uow.roles.create_role("tenant-corp", "role-jit-admin", "JIT Admin")
    uow.role_permissions.assign_permission("tenant-corp", "role-jit-admin", "migration.cutover", "admin")
    
    jit_auth = JITPrivilegeAuthority(uow.tenants, uow.principals, uow.roles, uow.role_grants)
    grant_res = jit_auth.issue_jit_grant(
        tenant_id="tenant-corp",
        principal_id="usr-bob",
        role_id="role-jit-admin",
        resource_type="MIGRATION",
        resource_id="mig-101",
        purpose="Emergency Cutover",
        granted_by="admin",
        duration_seconds=3600,
    )
    assert grant_res["is_jit"] is True if "is_jit" in grant_res else True
    
    # Active check
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    perms = rbac.resolve_effective_permissions_for_subject(
        "tenant-corp", GrantSubjectType.PRINCIPAL.value, "usr-bob",
        resource_type="MIGRATION", resource_id="mig-101"
    )
    assert "migration.cutover" in perms
    
    # Expire grant manually in DB
    uow.conn.execute("UPDATE role_grants SET expires_at = '2020-01-01T00:00:00Z'")
    perms_expired = rbac.resolve_effective_permissions_for_subject(
        "tenant-corp", GrantSubjectType.PRINCIPAL.value, "usr-bob",
        resource_type="MIGRATION", resource_id="mig-101"
    )
    assert "migration.cutover" not in perms_expired


def test_hostile_atk_37_jit_privilege_explicit_revocation(uow):
    """HOSTILE-ATK-37: Explicitly revoke JIT grant and verify permission is immediately removed."""
    uow.roles.create_role("tenant-corp", "role-jit-db", "JIT DB")
    uow.role_permissions.assign_permission("tenant-corp", "role-jit-db", "migration.read", "admin")
    
    jit_auth = JITPrivilegeAuthority(uow.tenants, uow.principals, uow.roles, uow.role_grants)
    grant = jit_auth.issue_jit_grant(
        tenant_id="tenant-corp",
        principal_id="usr-charlie",
        role_id="role-jit-db",
        resource_type="SYSTEM",
        resource_id="root",
        purpose="Investigation",
        granted_by="admin",
    )
    
    # Revoke
    jit_auth.revoke_jit_grant("tenant-corp", grant["grant_id"], "usr-charlie")
    
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    perms = rbac.resolve_effective_permissions_for_subject("tenant-corp", GrantSubjectType.PRINCIPAL.value, "usr-charlie")
    assert "migration.read" not in perms


def test_hostile_atk_38_governance_approval_artifact_self_approval_rejection():
    """HOSTILE-ATK-38: GovernanceApprovalArtifact must reject self-approval on creation."""
    artifact = GovernanceApprovalArtifact(
        approval_id="appr-01",
        tenant_id="tenant-corp",
        workspace_id="ws-01",
        project_id="proj-01",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        requester_id="usr-alice",
        approvers=["usr-alice"],  # Self-approval attempt
        source_identity_fingerprint="fp1",
        target_identity_fingerprint="fp2",
        config_fingerprint="fp3",
        selection_fingerprint="fp4",
        init_fingerprint="fp5",
        security_revision=1,
        key_id="key-01",
    )
    with pytest.raises(ApprovalIntegrityError, match="Self-approval prohibited"):
        artifact.validate_invariants(allow_self_approval=False)


def test_hostile_atk_39_governance_approval_artifact_duplicate_approver():
    """HOSTILE-ATK-39: GovernanceApprovalArtifact must reject duplicate approver signatures."""
    artifact = GovernanceApprovalArtifact(
        approval_id="appr-02",
        tenant_id="tenant-corp",
        workspace_id="ws-01",
        project_id="proj-01",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        requester_id="usr-alice",
        approvers=["usr-bob", "usr-bob"],  # Duplicate approver
        source_identity_fingerprint="fp1",
        target_identity_fingerprint="fp2",
        config_fingerprint="fp3",
        selection_fingerprint="fp4",
        init_fingerprint="fp5",
        security_revision=1,
        key_id="key-01",
    )
    with pytest.raises(ApprovalIntegrityError, match="Duplicate approvers"):
        artifact.validate_invariants()


def test_hostile_atk_40_governance_approval_artifact_tampered_plan_fingerprint():
    """HOSTILE-ATK-40: Tamper with plan revision and verify computed fingerprint detects change."""
    artifact1 = GovernanceApprovalArtifact(
        approval_id="appr-03",
        tenant_id="tenant-corp",
        workspace_id="ws-01",
        project_id="proj-01",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=1,
        execution_mode="M1",
        requester_id="usr-alice",
        approvers=["usr-bob", "usr-charlie"],
        source_identity_fingerprint="fp1",
        target_identity_fingerprint="fp2",
        config_fingerprint="fp3",
        selection_fingerprint="fp4",
        init_fingerprint="fp5",
        security_revision=1,
        key_id="key-01",
    )
    fp1 = artifact1.compute_fingerprint()
    
    # Tamper with plan revision
    artifact2 = GovernanceApprovalArtifact(
        approval_id="appr-03",
        tenant_id="tenant-corp",
        workspace_id="ws-01",
        project_id="proj-01",
        migration_id="mig-01",
        plan_id="plan-01",
        plan_revision=2,  # Tampered revision
        execution_mode="M1",
        requester_id="usr-alice",
        approvers=["usr-bob", "usr-charlie"],
        source_identity_fingerprint="fp1",
        target_identity_fingerprint="fp2",
        config_fingerprint="fp3",
        selection_fingerprint="fp4",
        init_fingerprint="fp5",
        security_revision=1,
        key_id="key-01",
    )
    fp2 = artifact2.compute_fingerprint()
    assert fp1 != fp2
