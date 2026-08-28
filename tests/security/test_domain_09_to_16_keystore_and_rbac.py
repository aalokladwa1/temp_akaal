"""tests.security.test_domain_09_to_16_keystore_and_rbac
===================================================
Hostile security tests for KeyStore, Key Lifecycles, RBAC, Roles, and Permissions (Domains 9-16).
"""

import pytest
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import GrantResourceType, GrantSubjectType, KeyAlgorithm, KeyPurpose
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.security.keystore import (
    KeyNotFoundError,
    KeyPurposeMismatchError,
    KeyRevokedError,
    KeyStoreAuthority,
    MasterRootKeyMissingError,
)
from akaalPipeline.security.permission_registry import PermissionRegistry, UnknownPermissionError
from akaalPipeline.security.rbac import CyclicRoleInheritanceError, RBACAuthority
from akaalPipeline.state.repositories import (
    SQLiteKeyringRepository,
    SQLiteRoleGrantRepository,
    SQLiteRolePermissionRepository,
    SQLiteRoleRepository,
    SQLiteTenantRepository,
)
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


@pytest.fixture
def uow():
    unit = SQLiteUnitOfWork(db_path=":memory:")
    tenant_repo = SQLiteTenantRepository(unit.connection)
    tenant_repo.create("tenant-1", "Test Tenant Beta", "ACTIVE", TimeAuthority.utc_iso_now())
    return unit


def test_keystore_mrk_resolution_and_fail_closed(uow):
    k_repo = SQLiteKeyringRepository(uow.connection)

    # 1. Missing MRK fails closed
    with pytest.raises(MasterRootKeyMissingError):
        KeyStoreAuthority(k_repo, master_root_key=None)

    # 2. Invalid length MRK fails closed
    with pytest.raises(MasterRootKeyMissingError):
        KeyStoreAuthority(k_repo, master_root_key=b"too-short")

    # 3. Valid 32-byte MRK succeeds
    valid_mrk = b"\x01" * 32
    keystore = KeyStoreAuthority(k_repo, master_root_key=valid_mrk)
    keystore.initialize_purpose_keys_if_missing()

    # 4. Key purpose separation
    key_id, priv_key = keystore.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)
    assert key_id is not None
    assert priv_key is not None

    # 5. Purpose mismatch rejection
    rec = k_repo.get_active_key(KeyPurpose.EXECUTION_SIGNING.value)
    k_repo.save_key(
        key_id="corrupt-key",
        purpose=KeyPurpose.TOKEN_ENCRYPT.value,
        algorithm=KeyAlgorithm.ED25519.value,
        public_key_pem="dummy",
        encrypted_private_key_blob=rec["encrypted_private_key_blob"],
    )
    with pytest.raises(KeyPurposeMismatchError):
        keystore.get_key_for_purpose("corrupt-key", KeyPurpose.EXECUTION_SIGNING)


def test_key_rotation_and_revocation(uow):
    k_repo = SQLiteKeyringRepository(uow.connection)
    keystore = KeyStoreAuthority(k_repo, master_root_key=b"\x02" * 32)
    keystore.initialize_purpose_keys_if_missing()

    key_id_1, _ = keystore.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)

    # Rotate key
    key_id_2 = keystore.rotate_key(KeyPurpose.EXECUTION_SIGNING)
    assert key_id_1 != key_id_2

    # Active key is now key_id_2
    active_id, _ = keystore.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)
    assert active_id == key_id_2

    # Revoking active key makes it unavailable
    keystore.revoke_key(key_id_2)
    with pytest.raises(KeyNotFoundError):
        keystore.get_signing_key_ed25519(KeyPurpose.EXECUTION_SIGNING)


def test_permission_registry_fail_closed_validation():
    # Valid permissions
    assert PermissionRegistry.is_valid("migration.create") is True
    assert PermissionRegistry.is_valid("migration.execute") is True
    assert PermissionRegistry.is_valid("security.key.rotate") is True

    # Unknown permissions fail closed
    assert PermissionRegistry.is_valid("arbitrary.malicious.permission") is False
    with pytest.raises(UnknownPermissionError):
        PermissionRegistry.assert_valid("invalid.perm")


def test_rbac_role_hierarchy_and_cycle_detection(uow):
    role_repo = SQLiteRoleRepository(uow.connection)
    perm_repo = SQLiteRolePermissionRepository(uow.connection)
    grant_repo = SQLiteRoleGrantRepository(uow.connection)
    cfg = SecurityBaselineConfig(max_role_inheritance_depth=5)
    rbac = RBACAuthority(role_repo, perm_repo, grant_repo, config=cfg)

    # Create role chain: JuniorDev -> SeniorDev -> TechLead
    role_repo.create_role("rol-junior", "tenant-1", "JuniorDev")
    role_repo.create_role("rol-senior", "tenant-1", "SeniorDev", parent_role_id="rol-junior")
    role_repo.create_role("rol-lead", "tenant-1", "TechLead", parent_role_id="rol-senior")

    perm_repo.add_permission("tenant-1", "rol-junior", "migration.read")
    perm_repo.add_permission("tenant-1", "rol-senior", "migration.create")
    perm_repo.add_permission("tenant-1", "rol-lead", "migration.execute")

    # Resolve hierarchy for TechLead: should inherit Junior and Senior perms
    perms = rbac.resolve_permissions_for_roles("tenant-1", {"rol-lead"})
    assert "migration.read" in perms
    assert "migration.create" in perms
    assert "migration.execute" in perms

    # Create cycle: JuniorDev -> parent is TechLead!
    uow.connection.execute("UPDATE enterprise_roles SET parent_role_id = 'rol-lead' WHERE role_id = 'rol-junior'")
    with pytest.raises(CyclicRoleInheritanceError):
        rbac.resolve_permissions_for_roles("tenant-1", {"rol-lead"})


def test_rbac_hierarchical_scoping(uow):
    role_repo = SQLiteRoleRepository(uow.connection)
    perm_repo = SQLiteRolePermissionRepository(uow.connection)
    grant_repo = SQLiteRoleGrantRepository(uow.connection)
    rbac = RBACAuthority(role_repo, perm_repo, grant_repo)

    role_repo.create_role("rol-editor", "tenant-1", "Editor")
    perm_repo.add_permission("tenant-1", "rol-editor", "migration.configure")

    # Create principal in DB
    uow.connection.execute(
        "INSERT INTO enterprise_principals (principal_id, tenant_id, principal_type, username, created_at, updated_at) VALUES ('usr-charlie', 'tenant-1', 'HUMAN', 'charlie', '2026-01-01', '2026-01-01')"
    )

    # Grant role at ORGANIZATION level
    grant_repo.create_grant(
        grant_id="grt-1",
        tenant_id="tenant-1",
        subject_type="PRINCIPAL",
        subject_id="usr-charlie",
        role_id="rol-editor",
        resource_type="ORGANIZATION",
        resource_id="tenant-1",
        granted_by="usr-charlie",
        granted_at=TimeAuthority.utc_iso_now(),
    )

    # Effective permissions under ORGANIZATION scope
    effective = rbac.get_effective_permissions(
        tenant_id="tenant-1",
        principal_id="usr-charlie",
        group_ids=[],
        req_resource_type="ORGANIZATION",
        req_resource_id="tenant-1",
    )
    assert "migration.configure" in effective

    # Revoke grant
    grant_repo.revoke_grant("tenant-1", "grt-1", TimeAuthority.utc_iso_now())
    effective_after_revoke = rbac.get_effective_permissions(
        tenant_id="tenant-1",
        principal_id="usr-charlie",
        group_ids=[],
        req_resource_type="ORGANIZATION",
        req_resource_id="tenant-1",
    )
    assert "migration.configure" not in effective_after_revoke
