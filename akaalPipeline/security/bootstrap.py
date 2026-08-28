"""akaalPipeline.security.bootstrap
====================================
Canonical Enterprise Bootstrap Coordinator.
Performs single initial bootstrap of Master Root Key, initial tenant, admin principal, and default roles.
Guarantees exactly-one bootstrap execution with concurrency serialization.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from akaal.core.crypto_random import generate_secure_id
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import KeyAlgorithm, KeyPurpose, PrincipalType
from akaalPipeline.contracts.errors import ConflictError, PersistenceError
from akaalPipeline.identity.passwords import PasswordAuthenticationEngine
from akaalPipeline.security.config import SecurityBaselineConfig
from akaalPipeline.security.keystore import KeyStoreAuthority
from akaalPipeline.security.permission_registry import PermissionRegistry
from akaalPipeline.state.repositories import (
    SQLiteCredentialRepository,
    SQLiteKeyringRepository,
    SQLitePrincipalRepository,
    SQLiteRoleGrantRepository,
    SQLiteRolePermissionRepository,
    SQLiteRoleRepository,
    SQLiteTenantRepository,
)
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork


class EnterpriseBootstrapCoordinator:
    """Coordinates one-time enterprise security bootstrap."""

    def __init__(
        self,
        uow: SQLiteUnitOfWork,
        config: Optional[SecurityBaselineConfig] = None,
        master_root_key: Optional[bytes] = None,
    ) -> None:
        self.uow = uow
        self.config = config or SecurityBaselineConfig()
        self.mrk = master_root_key or (b"\xaa" * 32)
        self.password_engine = PasswordAuthenticationEngine(self.config)

    def is_bootstrapped(self) -> bool:
        """Check if platform has already been bootstrapped."""
        conn = self.uow.connection
        cur = conn.execute("SELECT COUNT(*) as cnt FROM enterprise_tenants")
        row = cur.fetchone()
        return (row["cnt"] if row else 0) > 0

    def bootstrap(
        self,
        initial_tenant_id: str,
        initial_tenant_name: str,
        admin_username: str,
        admin_password: str,
        admin_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute one-time enterprise bootstrap ceremony.
        Raises ConflictError if system is already bootstrapped.
        """
        with self.uow:
            conn = self.uow.connection
            cur = conn.execute("SELECT COUNT(*) as cnt FROM enterprise_tenants")
            row = cur.fetchone()
            if row and row["cnt"] > 0:
                raise ConflictError("Enterprise security foundation is already bootstrapped")

            tenant_repo = SQLiteTenantRepository(conn)
            principal_repo = SQLitePrincipalRepository(conn)
            credential_repo = SQLiteCredentialRepository(conn)
            role_repo = SQLiteRoleRepository(conn)
            role_perm_repo = SQLiteRolePermissionRepository(conn)
            role_grant_repo = SQLiteRoleGrantRepository(conn)
            keyring_repo = SQLiteKeyringRepository(conn)

            keystore = KeyStoreAuthority(keyring_repo, master_root_key=self.mrk, config=self.config)
            keystore.initialize_purpose_keys_if_missing()

            now_iso = TimeAuthority.utc_iso_now()

            # 1. Create Initial Tenant
            tenant_repo.create(initial_tenant_id, initial_tenant_name, "ACTIVE", now_iso)

            # 2. Create Initial Admin Principal
            admin_principal_id = generate_secure_id("usr")
            principal_repo.create(
                tenant_id=initial_tenant_id,
                principal_id=admin_principal_id,
                principal_type=PrincipalType.HUMAN.value,
                username=admin_username,
                display_name="Enterprise Administrator",
                email=admin_email,
                created_at=now_iso,
            )

            # 3. Hash & Store Admin Password
            algo, kdf_params, salt_hex, pwd_hash = self.password_engine.hash_password(admin_password)
            credential_repo.save_credential(
                credential_id=generate_secure_id("crd"),
                tenant_id=initial_tenant_id,
                principal_id=admin_principal_id,
                kdf_algorithm=algo,
                kdf_params=kdf_params,
                salt_hex=salt_hex,
                password_hash_hex=pwd_hash,
                version=1,
                created_at=now_iso,
            )

            # 4. Create Builtin Administrator Role
            admin_role_id = generate_secure_id("rol")
            role_repo.create_role(
                role_id=admin_role_id,
                tenant_id=initial_tenant_id,
                name="PlatformAdministrator",
                description="Builtin full platform administrator",
                is_builtin=True,
                created_at=now_iso,
            )

            # Assign all canonical permissions to PlatformAdministrator role
            for perm in PermissionRegistry.ALL_PERMISSIONS:
                role_perm_repo.add_permission(initial_tenant_id, admin_role_id, perm)

            # 5. Grant Administrator Role to Admin Principal across the Tenant
            role_grant_repo.create_grant(
                grant_id=generate_secure_id("grt"),
                tenant_id=initial_tenant_id,
                subject_type="PRINCIPAL",
                subject_id=admin_principal_id,
                role_id=admin_role_id,
                resource_type="ORGANIZATION",
                resource_id=initial_tenant_id,
                granted_by=admin_principal_id,
                granted_at=now_iso,
            )

        return {
            "tenant_id": initial_tenant_id,
            "admin_principal_id": admin_principal_id,
            "admin_username": admin_username,
            "admin_role_id": admin_role_id,
            "status": "BOOTSTRAP_COMPLETED",
        }
