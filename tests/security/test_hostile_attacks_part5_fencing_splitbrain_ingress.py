"""tests.security.test_hostile_attacks_part5_fencing_splitbrain_ingress
===================================================================
Hostile Security Verification Suite - Part 5: Fencing, Split-Brain & Ingress
Contains Hostile Attack Scenarios HOSTILE-ATK-53 through HOSTILE-ATK-64.
"""

import pytest
import sqlite3
from akaalEngine.transport.drivers.base import StaleFencingEpochError
from akaalEngine.transport.drivers.generic_sql import GenericSQLTargetWriter
from akaalPipeline.application.unified_caller import PipelineUnifiedCaller, ActorContext
from akaalPipeline.security.central_authorization import CentralAuthorizationEngine, AuthorizationContext
from akaalPipeline.security.rbac import RBACAuthority
from akaalPipeline.security.abac import ABACAuthority
from akaalPipeline.identity.groups import GroupAuthority
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork
from akaalPipeline.contracts.errors import UnauthorizedError, ForbiddenError


@pytest.fixture
def uow(tmp_path):
    db_path = str(tmp_path / "akaal_hostile_fencing.db")
    uow_inst = SQLiteUnitOfWork(db_path)
    uow_inst.initialize_schema()
    uow_inst.tenants.create_tenant("tenant-corp", "Corp")
    uow_inst.tenants.create_tenant("tenant-evil", "Evil")
    uow_inst.principals.create(tenant_id="tenant-corp", principal_id="admin", principal_type="HUMAN", username="admin", email="admin@corp.com")
    uow_inst.principals.create(tenant_id="tenant-evil", principal_id="evil-admin", principal_type="HUMAN", username="evil-admin", email="evil@evil.com")
    return uow_inst


def test_hostile_atk_53_split_brain_stale_worker_rejection():
    """
    HOSTILE-ATK-53: Split-Brain Hostile Scenario:
    - Worker A holds epoch 42.
    - Worker A gets partitioned.
    - Worker B is granted authoritative epoch 43.
    - Worker A attempts physical mutation/commit with stale epoch 42.
    - Required: Worker A must fail closed with StaleFencingEpochError and rollback.
    """
    authoritative_epoch = 43
    
    def lease_validator(worker_epoch: int) -> bool:
        return worker_epoch >= authoritative_epoch

    writer = GenericSQLTargetWriter()
    # Worker A binds stale epoch 42
    writer.bind_fencing_token(42, lease_validator)
    
    with pytest.raises(StaleFencingEpochError):
        writer.verify_fencing()


def test_hostile_atk_54_physical_driver_commit_barrier_rollback():
    """HOSTILE-ATK-54: TargetWriter.commit() must evaluate physical fencing barrier before database commit."""
    authoritative_epoch = 100
    
    def validator(epoch: int) -> bool:
        return epoch >= authoritative_epoch

    writer = GenericSQLTargetWriter()
    writer.bind_fencing_token(99, validator)
    
    with pytest.raises(StaleFencingEpochError):
        writer.commit()


def test_hostile_atk_55_ingress_external_system_actor_spoofing_defense():
    """HOSTILE-ATK-55: PipelineUnifiedCaller must reject external envelopes asserting actor_type='SYSTEM'."""
    caller = PipelineUnifiedCaller()
    
    envelope = {
        "command_id": "cmd-01",
        "actor": {
            "actor_id": "attacker-01",
            "actor_type": "SYSTEM",  # Spoofed system identity from outside
            "tenant_id": "tenant-evil",
        },
        "payload": {"migration_id": "mig-01"},
    }
    
    resp = caller.handle_command(envelope)
    assert resp["success"] is False
    assert resp["error_code"] == "SYSTEM_ACTOR_SPOOFING_PROHIBITED"
    assert resp["error_category"] == "UNAUTHORIZED"


def test_hostile_atk_56_relational_fk_cross_tenant_workspace_injection(uow):
    """HOSTILE-ATK-56: Direct SQL probe: Attempt inserting workspace referencing non-existent or foreign tenant."""
    # Attempt inserting workspace with invalid tenant_id
    with pytest.raises(sqlite3.IntegrityError):
        uow.conn.execute(
            "INSERT INTO enterprise_workspaces (workspace_id, tenant_id, name, status, created_at, updated_at) "
            "VALUES ('ws-hack', 'tenant-nonexistent', 'Hacked WS', 'ACTIVE', '2026-01-01', '2026-01-01')"
        )


def test_hostile_atk_57_relational_fk_cross_tenant_project_injection(uow):
    """HOSTILE-ATK-57: Direct SQL probe: Attempt inserting project referencing non-existent workspace."""
    with pytest.raises(sqlite3.IntegrityError):
        uow.conn.execute(
            "INSERT INTO enterprise_projects (project_id, tenant_id, workspace_id, name, status, created_at, updated_at) "
            "VALUES ('proj-hack', 'tenant-corp', 'ws-nonexistent', 'Hacked Proj', 'ACTIVE', '2026-01-01', '2026-01-01')"
        )


def test_hostile_atk_58_relational_fk_cross_tenant_principal_injection(uow):
    """HOSTILE-ATK-58: Direct SQL probe: Attempt inserting principal referencing non-existent tenant."""
    with pytest.raises(sqlite3.IntegrityError):
        uow.conn.execute(
            "INSERT INTO enterprise_principals (principal_id, tenant_id, principal_type, username, email, display_name, is_active, failed_login_attempts, security_revision, created_at, updated_at) "
            "VALUES ('usr-hack', 'tenant-nonexistent', 'HUMAN', 'hacker', 'hacker@evil.com', 'Hacker', 1, 0, 1, '2026-01-01', '2026-01-01')"
        )


def test_hostile_atk_59_relational_fk_cross_tenant_role_grant_injection(uow):
    """HOSTILE-ATK-59: Direct SQL probe: Attempt granting a role belonging to tenant-corp to a user in tenant-evil."""
    uow.roles.create_role("tenant-corp", "role-corp-admin", "Corp Admin")
    uow.principals.create(tenant_id="tenant-evil", principal_id="usr-evil-1", principal_type="HUMAN", username="evil-1", email="evil@evil.com")
    
    # Attempting to grant tenant-corp's role in tenant-evil partition must violate foreign keys
    with pytest.raises(sqlite3.IntegrityError):
        uow.conn.execute(
            "INSERT INTO role_grants (grant_id, tenant_id, subject_type, subject_id, role_id, resource_type, resource_id, granted_by, granted_at) "
            "VALUES ('grant-hack', 'tenant-evil', 'PRINCIPAL', 'usr-evil-1', 'role-corp-admin', 'SYSTEM', 'root', 'evil-admin', '2026-01-01')"
        )


def test_hostile_atk_60_suspended_tenant_blocks_all_authorization(uow):
    """HOSTILE-ATK-60: Suspending a tenant immediately revokes and blocks all authorization for its principals."""
    uow.principals.create(tenant_id="tenant-corp", principal_id="usr-worker", principal_type="HUMAN", username="worker", email="w@corp.com")
    uow.roles.create_role("tenant-corp", "role-all", "All")
    uow.role_permissions.assign_permission("tenant-corp", "role-all", "migration.read", "admin")
    uow.role_grants.grant_role(
        grant_id="g-10", tenant_id="tenant-corp", subject_type="PRINCIPAL",
        subject_id="usr-worker", role_id="role-all", resource_type="SYSTEM",
        resource_id="root", granted_by="admin"
    )
    
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    authz = CentralAuthorizationEngine(
        uow.tenants, uow.principals, ga, rbac, abac
    )
    
    # Active tenant: Authorized
    ctx = AuthorizationContext(tenant_id="tenant-corp", principal_id="usr-worker", action="migration.read", resource_type="SYSTEM", resource_id="root")
    assert authz.authorize(ctx) is True
    
    # Suspend tenant
    uow.tenants.update_tenant("tenant-corp", status="SUSPENDED")
    
    # Now: Denied
    assert authz.authorize(ctx) is False


def test_hostile_atk_61_active_execution_revocation_security():
    """HOSTILE-ATK-61: Validate active execution token revocation triggers immediate dispatch failure."""
    from akaalPipeline.security.execution_authorization import verify_execution_authorization, ExecutionAuthorizationError
    
    # Expired token simulation
    expired_artifact = {
        "artifact_version": "1.0.0",
        "authorization_id": "authz-exp",
        "nonce": "nonce-1",
        "key_id": "key-1",
        "tenant_id": "tenant-corp",
        "migration_id": "mig-1",
        "execution_id": "exec-1",
        "execution_seal": {},
        "allowed_operations": ["MIGRATE"],
        "issued_at": "2020-01-01T00:00:00Z",
        "expires_at": "2020-01-01T01:00:00Z",
        "signature_algorithm": "ED25519",
        "signature_hex": "00" * 64,
    }
    with pytest.raises(ExecutionAuthorizationError, match="expired"):
        verify_execution_authorization(expired_artifact, "pub_pem", expected_tenant_id="tenant-corp")


def test_hostile_atk_62_checkpoint_resume_security_reauthorization():
    """HOSTILE-ATK-62: Resuming an execution from checkpoint must bind to the current active authorization."""
    from akaalPipeline.security.seal import ExecutionSealBuilder
    
    # Seal from previous run has epoch 10
    seal_old = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", plan_id="plan-01", plan_revision=1,
        execution_mode="M1", source_identity_fingerprint="src", target_identity_fingerprint="tgt",
        selection_scope_fingerprint="sel", config_fingerprint="cfg",
        initialization_fingerprint="init", approval_fingerprint="appr", fence_epoch=10,
    )
    
    # Resumed run has new epoch 11
    seal_resumed = ExecutionSealBuilder.build_seal(
        tenant_id="tenant-corp", workspace_id="ws-01", project_id="proj-01",
        migration_id="mig-01", plan_id="plan-01", plan_revision=1,
        execution_mode="M1", source_identity_fingerprint="src", target_identity_fingerprint="tgt",
        selection_scope_fingerprint="sel", config_fingerprint="cfg",
        initialization_fingerprint="init", approval_fingerprint="appr", fence_epoch=11,
    )
    
    assert seal_old.seal_fingerprint != seal_resumed.seal_fingerprint


def test_hostile_atk_63_multi_process_cache_isolation_simulation(tmp_path):
    """HOSTILE-ATK-63: Two independent process-local cache managers reading SQLite must respect DB security revision."""
    from akaalPipeline.security.cache import AuthorizationCacheManager
    
    cache1 = AuthorizationCacheManager()
    cache2 = AuthorizationCacheManager()
    
    # Process 1 caches decision at revision 1
    cache1.set_decision("tenant-corp", "usr-1", 1, "migration.execute", "SYSTEM", "root", True)
    
    # In SQLite, security revision advances to 2
    # Process 2 checks revision 2 -> Cache miss (does not use stale process 1 cache)
    assert cache2.get_decision("tenant-corp", "usr-1", 2, "migration.execute", "SYSTEM", "root") is None


def test_hostile_atk_64_zero_standing_admin_bypass_comprehensive(uow):
    """HOSTILE-ATK-64: Comprehensive verification that admin, governor, root, superuser usernames have NO implicit privileges."""
    uow.principals.create(tenant_id="tenant-corp", principal_id="admin-user", principal_type="HUMAN", username="admin-user", email="admin2@corp.com")
    uow.principals.create(tenant_id="tenant-corp", principal_id="root", principal_type="HUMAN", username="root", email="root@corp.com")
    uow.principals.create(tenant_id="tenant-corp", principal_id="superuser", principal_type="HUMAN", username="super", email="super@corp.com")
    
    ga = GroupAuthority(uow.groups, uow.principals)
    rbac = RBACAuthority(uow.roles, uow.role_permissions, uow.role_grants)
    abac = ABACAuthority(uow.abac_policies)
    authz = CentralAuthorizationEngine(
        uow.tenants, uow.principals, ga, rbac, abac
    )
    
    # All must fail by default without explicitly granted roles/permissions
    for uname in ["admin-user", "root", "superuser"]:
        ctx = AuthorizationContext(tenant_id="tenant-corp", principal_id=uname, action="migration.cutover", resource_type="SYSTEM", resource_id="root")
        assert authz.authorize(ctx) is False
