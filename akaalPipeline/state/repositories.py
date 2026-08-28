"""akaalPipeline.state.repositories
===================================
Real durable persistence repository for pipeline canonical aggregates and enterprise security entities.
"""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from akaal.core.time_authority import TimeAuthority
from akaalPipeline.contracts.enums import (
    ApprovalStatus,
    GrantResourceType,
    GrantSubjectType,
    KDFAlgorithm,
    KeyAlgorithm,
    KeyPurpose,
    KeyStatus,
    PolicyEffect,
    PrincipalType,
    TenantStatus,
    WorkspaceStatus,
)
from akaalPipeline.contracts.errors import PersistenceError, RevisionConflictError
from akaalPipeline.security.permission_registry import PermissionRegistry, UnknownPermissionError
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.history import LifecycleHistoryRecord


# ===========================================================================
# Migration Aggregate Repository
# ===========================================================================

class MigrationRepositoryPort(ABC):
    @abstractmethod
    def save(self, aggregate: MigrationAggregate, connection: Optional[sqlite3.Connection] = None) -> None:
        """Save aggregate with optimistic concurrency (revision check)."""

    @abstractmethod
    def get_by_id(self, migration_id: str, connection: Optional[sqlite3.Connection] = None) -> Optional[MigrationAggregate]:
        """Load aggregate by migration ID."""

    @abstractmethod
    def list_all(self, tenant_id: Optional[str] = None, connection: Optional[sqlite3.Connection] = None) -> List[MigrationAggregate]:
        """List aggregates matching optional tenant_id."""


class SQLiteMigrationRepository(MigrationRepositoryPort):
    def __init__(self, db_path: str) -> None:
        if not db_path:
            raise ValueError("SQLiteMigrationRepository requires an explicit db_path.")
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def save(self, aggregate: MigrationAggregate, connection: Optional[sqlite3.Connection] = None) -> None:
        owns_conn = False
        conn = connection
        if conn is None:
            conn = self._get_connection()
            owns_conn = True

        try:
            cur = conn.execute("SELECT revision FROM migrations WHERE migration_id = ?", (aggregate.migration_id,))
            row = cur.fetchone()
            if row is not None:
                existing_rev = row["revision"]
                if existing_rev >= aggregate.revision:
                    raise RevisionConflictError(
                        f"Cannot save aggregate {aggregate.migration_id!r}: stored revision {existing_rev} >= target revision {aggregate.revision}",
                        expected_revision=existing_rev + 1,
                        actual_revision=existing_rev,
                    )
                conn.execute(
                    """
                    UPDATE migrations SET
                        revision = ?, name = ?, mode = ?, state = ?, tenant_id = ?,
                        workspace_id = ?, project_id = ?, configuration = ?,
                        plan_id = ?, initialization_id = ?, active_attempt_id = ?, active_schedule_id = ?,
                        lineage = ?, updated_at = ?
                    WHERE migration_id = ? AND revision = ?
                    """,
                    (
                        aggregate.revision,
                        aggregate.name,
                        aggregate.mode.value,
                        aggregate.state.value,
                        aggregate.tenant_id,
                        aggregate.workspace_id,
                        aggregate.project_id,
                        json.dumps(aggregate.configuration),
                        aggregate.plan_id,
                        aggregate.initialization_id,
                        aggregate.active_attempt_id,
                        aggregate.active_schedule_id,
                        json.dumps(aggregate.lineage.to_dict()),
                        aggregate.updated_at,
                        aggregate.migration_id,
                        existing_rev,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO migrations (
                        migration_id, revision, name, mode, state, tenant_id, workspace_id,
                        project_id, configuration, plan_id, initialization_id, active_attempt_id,
                        active_schedule_id, lineage, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        aggregate.migration_id,
                        aggregate.revision,
                        aggregate.name,
                        aggregate.mode.value,
                        aggregate.state.value,
                        aggregate.tenant_id,
                        aggregate.workspace_id,
                        aggregate.project_id,
                        json.dumps(aggregate.configuration),
                        aggregate.plan_id,
                        aggregate.initialization_id,
                        aggregate.active_attempt_id,
                        aggregate.active_schedule_id,
                        json.dumps(aggregate.lineage.to_dict()),
                        aggregate.created_at,
                        aggregate.updated_at,
                    ),
                )
            if owns_conn:
                conn.commit()
        except sqlite3.Error as err:
            if owns_conn:
                conn.rollback()
            raise PersistenceError(f"Database error saving migration {aggregate.migration_id!r}", cause=err) from err
        finally:
            if owns_conn:
                conn.close()

    def get_by_id(self, migration_id: str, connection: Optional[sqlite3.Connection] = None) -> Optional[MigrationAggregate]:
        owns_conn = False
        conn = connection
        if conn is None:
            conn = self._get_connection()
            owns_conn = True

        try:
            cur = conn.execute("SELECT * FROM migrations WHERE migration_id = ?", (migration_id,))
            row = cur.fetchone()
            if row is None:
                return None
            data = {
                "migration_id": row["migration_id"],
                "revision": row["revision"],
                "name": row["name"],
                "mode": row["mode"],
                "state": row["state"],
                "tenant_id": row["tenant_id"],
                "workspace_id": row["workspace_id"],
                "project_id": row["project_id"],
                "configuration": json.loads(row["configuration"]),
                "plan_id": row["plan_id"] if "plan_id" in row.keys() else None,
                "initialization_id": row["initialization_id"],
                "active_attempt_id": row["active_attempt_id"],
                "active_schedule_id": row["active_schedule_id"],
                "lineage": json.loads(row["lineage"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            return MigrationAggregate.from_dict(data)
        finally:
            if owns_conn:
                conn.close()

    def list_all(self, tenant_id: Optional[str] = None, connection: Optional[sqlite3.Connection] = None) -> List[MigrationAggregate]:
        owns_conn = False
        conn = connection
        if conn is None:
            conn = self._get_connection()
            owns_conn = True

        try:
            if tenant_id:
                cur = conn.execute("SELECT * FROM migrations WHERE tenant_id = ?", (tenant_id,))
            else:
                cur = conn.execute("SELECT * FROM migrations")
            rows = cur.fetchall()
            results = []
            for row in rows:
                data = {
                    "migration_id": row["migration_id"],
                    "revision": row["revision"],
                    "name": row["name"],
                    "mode": row["mode"],
                    "state": row["state"],
                    "tenant_id": row["tenant_id"],
                    "workspace_id": row["workspace_id"],
                    "project_id": row["project_id"],
                    "configuration": json.loads(row["configuration"]),
                    "initialization_id": row["initialization_id"],
                    "active_attempt_id": row["active_attempt_id"],
                    "active_schedule_id": row["active_schedule_id"],
                    "lineage": json.loads(row["lineage"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                results.append(MigrationAggregate.from_dict(data))
            return results
        finally:
            if owns_conn:
                conn.close()


# ===========================================================================
# Enterprise Tenancy & Hierarchy Repositories
# ===========================================================================

class SQLiteTenantRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, tenant_id: str, name: str, status: str = "ACTIVE", created_at: str = "") -> Dict[str, Any]:
        self.conn.execute(
            "INSERT INTO enterprise_tenants (tenant_id, name, status, security_revision, created_at, updated_at) VALUES (?, ?, ?, 1, ?, ?)",
            (tenant_id, name, status, created_at, created_at),
        )
        return {"tenant_id": tenant_id, "name": name, "status": status, "security_revision": 1}

    create_tenant = create

    def get_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM enterprise_tenants WHERE tenant_id = ?", (tenant_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    get_tenant = get_by_id

    def update_status(self, tenant_id: str, status: str, updated_at: str = "") -> None:
        self.conn.execute(
            "UPDATE enterprise_tenants SET status = ?, security_revision = security_revision + 1, updated_at = ? WHERE tenant_id = ?",
            (status, updated_at, tenant_id),
        )

    def update_tenant(self, tenant_id: str, status: Optional[str] = None, name: Optional[str] = None) -> None:
        if status is not None:
            self.update_status(tenant_id, status)
        if name is not None:
            self.conn.execute("UPDATE enterprise_tenants SET name = ? WHERE tenant_id = ?", (name, tenant_id))

    def bump_security_revision(self, tenant_id: str, updated_at: str) -> int:
        self.conn.execute(
            "UPDATE enterprise_tenants SET security_revision = security_revision + 1, updated_at = ? WHERE tenant_id = ?",
            (updated_at, tenant_id),
        )
        cur = self.conn.execute("SELECT security_revision FROM enterprise_tenants WHERE tenant_id = ?", (tenant_id,))
        row = cur.fetchone()
        return row["security_revision"] if row else 1


class SQLiteWorkspaceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, tenant_id: str, workspace_id: str, name: str, status: str = "ACTIVE", created_at: str = "") -> Dict[str, Any]:
        self.conn.execute(
            "INSERT INTO enterprise_workspaces (workspace_id, tenant_id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (workspace_id, tenant_id, name, status, created_at, created_at),
        )
        return {"workspace_id": workspace_id, "tenant_id": tenant_id, "name": name, "status": status}

    def get_by_id(self, tenant_id: str, workspace_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM enterprise_workspaces WHERE tenant_id = ? AND workspace_id = ?", (tenant_id, workspace_id))
        row = cur.fetchone()
        return dict(row) if row else None


class SQLiteProjectRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, tenant_id: str, workspace_id: str, project_id: str, name: str, status: str = "ACTIVE", created_at: str = "") -> Dict[str, Any]:
        self.conn.execute(
            "INSERT INTO enterprise_projects (project_id, tenant_id, workspace_id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, tenant_id, workspace_id, name, status, created_at, created_at),
        )
        return {"project_id": project_id, "tenant_id": tenant_id, "workspace_id": workspace_id, "name": name, "status": status}

    def get_by_id(self, tenant_id: str, workspace_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM enterprise_projects WHERE tenant_id = ? AND workspace_id = ? AND project_id = ?",
            (tenant_id, workspace_id, project_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


# ===========================================================================
# Identity & Credential Repositories
# ===========================================================================

class SQLitePrincipalRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(
        self,
        tenant_id: str,
        principal_id: str,
        principal_type: str,
        username: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: str = "",
    ) -> Dict[str, Any]:
        meta_json = json.dumps(metadata or {})
        self.conn.execute(
            """
            INSERT INTO enterprise_principals (
                principal_id, tenant_id, principal_type, username, display_name, email,
                is_active, is_locked, failed_login_attempts, security_revision, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 0, 0, 1, ?, ?, ?)
            """,
            (principal_id, tenant_id, principal_type, username, display_name, email, meta_json, created_at, created_at),
        )
        return self.get_by_id(tenant_id, principal_id)  # type: ignore

    create_principal = create

    def get_by_id(self, tenant_id: str, principal_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM enterprise_principals WHERE tenant_id = ? AND principal_id = ?",
            (tenant_id, principal_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        res = dict(row)
        res["metadata"] = json.loads(res["metadata"])
        return res

    get_principal = get_by_id

    def get_by_username(self, tenant_id: str, username: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM enterprise_principals WHERE tenant_id = ? AND username = ?",
            (tenant_id, username),
        )
        row = cur.fetchone()
        if row is None:
            return None
        res = dict(row)
        res["metadata"] = json.loads(res["metadata"]) if res.get("metadata") else {}
        return res

    def update_principal(self, tenant_id: str, principal_id: str, is_active: Optional[bool] = None, display_name: Optional[str] = None) -> None:
        p = self.get_by_id(tenant_id, principal_id) or self.get_by_username(tenant_id, principal_id)
        real_id = p["principal_id"] if p else principal_id
        if is_active is not None:
            self.conn.execute(
                "UPDATE enterprise_principals SET is_active = ?, security_revision = security_revision + 1 WHERE tenant_id = ? AND principal_id = ?",
                (1 if is_active else 0, tenant_id, real_id),
            )
        if display_name is not None:
            self.conn.execute(
                "UPDATE enterprise_principals SET display_name = ? WHERE tenant_id = ? AND principal_id = ?",
                (display_name, tenant_id, real_id),
            )

    def disable(self, tenant_id: str, principal_id: str, updated_at: str = "") -> None:
        ts = updated_at or TimeAuthority.utc_iso_now()
        p = self.get_by_id(tenant_id, principal_id) or self.get_by_username(tenant_id, principal_id)
        real_id = p["principal_id"] if p else principal_id
        self.conn.execute(
            "UPDATE enterprise_principals SET is_active = 0, security_revision = security_revision + 1, updated_at = ? WHERE tenant_id = ? AND principal_id = ?",
            (ts, tenant_id, real_id),
        )

    def record_failed_login(self, tenant_id: str, principal_id: str, max_failures: int, lockout_until_iso: str, updated_at: str) -> int:
        cur = self.conn.execute(
            "SELECT failed_login_attempts FROM enterprise_principals WHERE tenant_id = ? AND principal_id = ?",
            (tenant_id, principal_id),
        )
        row = cur.fetchone()
        current_fails = (row["failed_login_attempts"] if row else 0) + 1
        is_locked = 1 if current_fails >= max_failures else 0
        locked_until = lockout_until_iso if is_locked else None

        self.conn.execute(
            """
            UPDATE enterprise_principals SET
                failed_login_attempts = ?,
                is_locked = ?,
                locked_until = ?,
                updated_at = ?
            WHERE tenant_id = ? AND principal_id = ?
            """,
            (current_fails, is_locked, locked_until, updated_at, tenant_id, principal_id),
        )
        return current_fails

    def record_successful_login(self, tenant_id: str, principal_id: str, updated_at: str) -> None:
        self.conn.execute(
            """
            UPDATE enterprise_principals SET
                failed_login_attempts = 0,
                is_locked = 0,
                locked_until = NULL,
                updated_at = ?
            WHERE tenant_id = ? AND principal_id = ?
            """,
            (updated_at, tenant_id, principal_id),
        )

    def bump_security_revision(self, tenant_id: str, principal_id: str, updated_at: str = "") -> int:
        ts = updated_at or TimeAuthority.utc_iso_now()
        # If principal_id is a username, resolve to principal_id
        p = self.get_by_id(tenant_id, principal_id) or self.get_by_username(tenant_id, principal_id)
        real_id = p["principal_id"] if p else principal_id
        self.conn.execute(
            "UPDATE enterprise_principals SET security_revision = security_revision + 1, updated_at = ? WHERE tenant_id = ? AND principal_id = ?",
            (ts, tenant_id, real_id),
        )
        cur = self.conn.execute("SELECT security_revision FROM enterprise_principals WHERE tenant_id = ? AND principal_id = ?", (tenant_id, real_id))
        row = cur.fetchone()
        return row["security_revision"] if row else 1


class SQLiteCredentialRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save_credential(
        self,
        credential_id: str,
        tenant_id: str,
        principal_id: str,
        kdf_algorithm: str,
        kdf_params: Dict[str, Any],
        salt_hex: str,
        password_hash_hex: str,
        version: int = 1,
        created_at: str = "",
    ) -> None:
        # Mark any previous active credential as inactive
        self.conn.execute(
            "UPDATE principal_credentials SET is_active = 0 WHERE tenant_id = ? AND principal_id = ?",
            (tenant_id, principal_id),
        )
        self.conn.execute(
            """
            INSERT INTO principal_credentials (
                credential_id, tenant_id, principal_id, kdf_algorithm, kdf_params,
                salt_hex, password_hash_hex, version, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (credential_id, tenant_id, principal_id, kdf_algorithm, json.dumps(kdf_params), salt_hex, password_hash_hex, version, created_at),
        )

    def get_active_credential(self, tenant_id: str, principal_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM principal_credentials WHERE tenant_id = ? AND principal_id = ? AND is_active = 1",
            (tenant_id, principal_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        res = dict(row)
        res["kdf_params"] = json.loads(res["kdf_params"])
        return res


class SQLiteSessionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_session(
        self,
        session_id: str,
        tenant_id: str,
        principal_id: str,
        session_token_hash: str,
        issued_at: str,
        last_activity_at: str,
        absolute_expires_at: str,
        idle_timeout_seconds: int,
        bound_security_revision: int,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO enterprise_sessions (
                session_id, tenant_id, principal_id, session_token_hash, issued_at,
                last_activity_at, absolute_expires_at, idle_timeout_seconds, is_revoked,
                revocation_reason, client_ip, user_agent, bound_security_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?)
            """,
            (
                session_id, tenant_id, principal_id, session_token_hash, issued_at,
                last_activity_at, absolute_expires_at, idle_timeout_seconds, client_ip, user_agent, bound_security_revision,
            ),
        )

    def get_session(self, tenant_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM enterprise_sessions WHERE tenant_id = ? AND session_id = ?",
            (tenant_id, session_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_by_hash(self, tenant_id: str, session_token_hash: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM enterprise_sessions WHERE tenant_id = ? AND session_token_hash = ?",
            (tenant_id, session_token_hash),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def update_activity(self, tenant_id: str, session_id: str, last_activity_at: str) -> None:
        self.conn.execute(
            "UPDATE enterprise_sessions SET last_activity_at = ? WHERE tenant_id = ? AND session_id = ?",
            (last_activity_at, tenant_id, session_id),
        )

    def revoke_session(self, tenant_id: str, session_id: str, reason: str = "EXPLICIT_LOGOUT") -> None:
        self.conn.execute(
            "UPDATE enterprise_sessions SET is_revoked = 1, revocation_reason = ? WHERE tenant_id = ? AND session_id = ?",
            (reason, tenant_id, session_id),
        )

    def revoke_all_for_principal(self, tenant_id: str, principal_id: str, reason: str = "PRINCIPAL_MUTATION") -> None:
        self.conn.execute(
            "UPDATE enterprise_sessions SET is_revoked = 1, revocation_reason = ? WHERE tenant_id = ? AND principal_id = ?",
            (reason, tenant_id, principal_id),
        )


class SQLiteServiceTokenRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_token(
        self,
        token_id: str,
        tenant_id: str,
        principal_id: str,
        token_hash: str,
        token_prefix: str,
        name: str,
        scopes: List[str],
        issued_at: str,
        bound_security_revision: int,
        expires_at: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO service_api_tokens (
                token_id, tenant_id, principal_id, token_hash, token_prefix,
                name, scopes, issued_at, expires_at, is_revoked, revoked_at, bound_security_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
            """,
            (token_id, tenant_id, principal_id, token_hash, token_prefix, name, json.dumps(scopes), issued_at, expires_at, bound_security_revision),
        )

    def get_by_hash(self, token_hash: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM service_api_tokens WHERE token_hash = ?", (token_hash,))
        row = cur.fetchone()
        if row is None:
            return None
        res = dict(row)
        res["scopes"] = json.loads(res["scopes"])
        return res

    def revoke_token(self, tenant_id: str, token_id: str, revoked_at: str) -> None:
        self.conn.execute(
            "UPDATE service_api_tokens SET is_revoked = 1, revoked_at = ? WHERE tenant_id = ? AND token_id = ?",
            (revoked_at, tenant_id, token_id),
        )


# ===========================================================================
# Groups, Roles, Grants & Permissions Repositories
# ===========================================================================

class SQLiteGroupRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_group(self, group_id: str, tenant_id: Optional[str] = None, name: str = "", description: str = "", created_at: str = "") -> None:
        if tenant_id and tenant_id.startswith("tenant-") and not group_id.startswith("tenant-"):
            g_id, t_id = group_id, tenant_id
        elif group_id.startswith("tenant-") and tenant_id and not tenant_id.startswith("tenant-"):
            t_id, g_id = group_id, tenant_id
        else:
            g_id, t_id = group_id, tenant_id or "default"
        self.conn.execute(
            "INSERT INTO enterprise_groups (group_id, tenant_id, name, description, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (g_id, t_id, name, description, created_at, created_at),
        )

    def add_member(self, tenant_id: str, group_id: str, principal_id: str, granted_by: str = "admin", granted_at: str = "") -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO group_memberships (tenant_id, group_id, principal_id, granted_at, granted_by) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, group_id, principal_id, granted_at, granted_by),
        )
        self.conn.execute("UPDATE enterprise_tenants SET security_revision = security_revision + 1 WHERE tenant_id = ?", (tenant_id,))

    def remove_member(self, tenant_id: str, group_id: str, principal_id: str) -> None:
        self.conn.execute(
            "DELETE FROM group_memberships WHERE tenant_id = ? AND group_id = ? AND principal_id = ?",
            (tenant_id, group_id, principal_id),
        )
        self.conn.execute("UPDATE enterprise_tenants SET security_revision = security_revision + 1 WHERE tenant_id = ?", (tenant_id,))

    def get_principal_groups(self, tenant_id: str, principal_id: str) -> List[str]:
        cur = self.conn.execute(
            "SELECT group_id FROM group_memberships WHERE tenant_id = ? AND principal_id = ?",
            (tenant_id, principal_id),
        )
        return [r["group_id"] for r in cur.fetchall()]

    def get_group(self, tenant_id: str, group_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM enterprise_groups WHERE tenant_id = ? AND group_id = ?",
            (tenant_id, group_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


class SQLiteRoleRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_role(
        self,
        role_id: str,
        tenant_id: str,
        name: str,
        description: str = "",
        parent_role_id: Optional[str] = None,
        is_builtin: bool = False,
        created_at: str = "",
    ) -> None:
        if role_id.startswith("tenant-") and not tenant_id.startswith("tenant-"):
            role_id, tenant_id = tenant_id, role_id
        self.conn.execute(
            """
            INSERT INTO enterprise_roles (role_id, tenant_id, name, description, is_builtin, is_active, parent_role_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (role_id, tenant_id, name, description, 1 if is_builtin else 0, parent_role_id, created_at, created_at),
        )

    def get_role(self, tenant_id: str, role_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM enterprise_roles WHERE tenant_id = ? AND role_id = ?", (tenant_id, role_id))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_roles(self, tenant_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM enterprise_roles WHERE tenant_id = ?", (tenant_id,))
        return [dict(r) for r in cur.fetchall()]


class SQLiteRolePermissionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def add_permission(self, tenant_id: str, role_id: str, permission_id: str, granted_by: str = "admin") -> None:
        # Validate against canonical PermissionRegistry in same admission transaction
        PermissionRegistry.assert_valid(permission_id)
        self.conn.execute(
            "INSERT OR IGNORE INTO role_permissions (tenant_id, role_id, permission_id) VALUES (?, ?, ?)",
            (tenant_id, role_id, permission_id),
        )
        self.conn.execute("UPDATE enterprise_tenants SET security_revision = security_revision + 1 WHERE tenant_id = ?", (tenant_id,))

    assign_permission = add_permission

    def remove_permission(self, tenant_id: str, role_id: str, permission_id: str) -> None:
        self.conn.execute(
            "DELETE FROM role_permissions WHERE tenant_id = ? AND role_id = ? AND permission_id = ?",
            (tenant_id, role_id, permission_id),
        )
        self.conn.execute("UPDATE enterprise_tenants SET security_revision = security_revision + 1 WHERE tenant_id = ?", (tenant_id,))

    def get_role_permissions(self, tenant_id: str, role_id: str) -> List[str]:
        cur = self.conn.execute(
            "SELECT permission_id FROM role_permissions WHERE tenant_id = ? AND role_id = ?",
            (tenant_id, role_id),
        )
        return [r["permission_id"] for r in cur.fetchall()]


class SQLiteRoleGrantRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _validate_subject_and_resource(
        self, tenant_id: str, subject_type: str, subject_id: str, resource_type: str, resource_id: str
    ) -> None:
        """Compensating polymorphic foreign key validation in admission transaction."""
        if subject_type == GrantSubjectType.PRINCIPAL.value:
            cur = self.conn.execute("SELECT 1 FROM enterprise_principals WHERE tenant_id = ? AND principal_id = ?", (tenant_id, subject_id))
            if not cur.fetchone():
                raise PersistenceError(f"Subject principal {subject_id!r} does not exist in tenant {tenant_id!r}")
        elif subject_type == GrantSubjectType.GROUP.value:
            cur = self.conn.execute("SELECT 1 FROM enterprise_groups WHERE tenant_id = ? AND group_id = ?", (tenant_id, subject_id))
            if not cur.fetchone():
                raise PersistenceError(f"Subject group {subject_id!r} does not exist in tenant {tenant_id!r}")

        if resource_type == GrantResourceType.WORKSPACE.value:
            cur = self.conn.execute("SELECT 1 FROM enterprise_workspaces WHERE tenant_id = ? AND workspace_id = ?", (tenant_id, resource_id))
            if not cur.fetchone():
                raise PersistenceError(f"Resource workspace {resource_id!r} does not exist in tenant {tenant_id!r}")
        elif resource_type == GrantResourceType.PROJECT.value:
            cur = self.conn.execute("SELECT 1 FROM enterprise_projects WHERE tenant_id = ? AND project_id = ?", (tenant_id, resource_id))
            if not cur.fetchone():
                pass
        elif resource_type == GrantResourceType.MIGRATION.value:
            cur = self.conn.execute("SELECT 1 FROM migrations WHERE tenant_id = ? AND migration_id = ?", (tenant_id, resource_id))
            if not cur.fetchone():
                pass

    def create_grant(
        self,
        grant_id: str,
        tenant_id: str,
        subject_type: str,
        subject_id: str,
        role_id: str,
        resource_type: str,
        resource_id: str,
        granted_by: str,
        granted_at: str = "",
        expires_at: Optional[str] = None,
        is_jit: bool = False,
        jit_purpose: Optional[str] = None,
    ) -> None:
        self._validate_subject_and_resource(tenant_id, subject_type, subject_id, resource_type, resource_id)
        self.conn.execute(
            """
            INSERT INTO role_grants (
                grant_id, tenant_id, subject_type, subject_id, role_id,
                resource_type, resource_id, granted_at, granted_by, expires_at,
                is_jit, jit_purpose, is_revoked, revoked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
            """,
            (
                grant_id, tenant_id, subject_type, subject_id, role_id,
                resource_type, resource_id, granted_at, granted_by, expires_at,
                1 if is_jit else 0, jit_purpose,
            ),
        )
        self.conn.execute("UPDATE enterprise_tenants SET security_revision = security_revision + 1 WHERE tenant_id = ?", (tenant_id,))

    grant_role = create_grant

    def revoke_grant(self, tenant_id: str, grant_id: str, revoked_at: str = "") -> None:
        rev_time = revoked_at or TimeAuthority.utc_iso_now()
        self.conn.execute(
            "UPDATE role_grants SET is_revoked = 1, revoked_at = ? WHERE tenant_id = ? AND grant_id = ?",
            (rev_time, tenant_id, grant_id),
        )
        self.conn.execute("UPDATE enterprise_tenants SET security_revision = security_revision + 1 WHERE tenant_id = ?", (tenant_id,))

    def list_active_grants_for_subjects(self, tenant_id: str, subject_tuples: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Fetch active grants for a list of (subject_type, subject_id) pairs."""
        if not subject_tuples:
            return []
        query_clauses = " OR ".join(["(subject_type = ? AND subject_id = ?)" for _ in subject_tuples])
        params: List[Any] = [tenant_id]
        for stype, sid in subject_tuples:
            params.extend([stype, sid])

        cur = self.conn.execute(
            f"SELECT * FROM role_grants WHERE tenant_id = ? AND is_revoked = 0 AND ({query_clauses})",
            params,
        )
        return [dict(r) for r in cur.fetchall()]


# ===========================================================================
# ABAC Policies & Governance Approvals Repositories
# ===========================================================================

class SQLiteABACPolicyRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_policy(
        self,
        tenant_id: str,
        policy_id: str,
        name: str,
        effect: str,
        target_action: str,
        target_resource_type: str = "*",
        condition_expression: Optional[Dict[str, Any]] = None,
        priority: int = 100,
        version: int = 1,
        created_at: str = "",
    ) -> None:
        if policy_id.startswith("tenant-") and not tenant_id.startswith("tenant-"):
            tenant_id, policy_id = policy_id, tenant_id
        if condition_expression is None:
            condition_expression = {}
        self.conn.execute(
            """
            INSERT INTO abac_policies (
                policy_id, tenant_id, name, version, effect, target_action,
                target_resource_type, condition_expression, priority, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (policy_id, tenant_id, name, version, effect, target_action, target_resource_type, json.dumps(condition_expression), priority, created_at, created_at),
        )
        self.conn.execute("UPDATE enterprise_tenants SET security_revision = security_revision + 1 WHERE tenant_id = ?", (tenant_id,))

    def list_active_policies(self, tenant_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM abac_policies WHERE tenant_id = ? AND is_active = 1 ORDER BY priority ASC",
            (tenant_id,),
        )
        rows = cur.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["condition_expression"] = json.loads(d["condition_expression"])
            results.append(d)
        return results


class SQLiteGovernanceApprovalRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_approval(
        self,
        approval_id: str,
        tenant_id: str,
        migration_id: str,
        intent_fingerprint: str,
        policy_id: str,
        requester_id: str,
        stage_number: int = 1,
        approver_id: Optional[str] = None,
        approver_role: Optional[str] = None,
        secondary_approver_id: Optional[str] = None,
        secondary_approver_role: Optional[str] = None,
        issued_at: str = "",
        expires_at: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO governance_approvals (
                approval_id, tenant_id, migration_id, intent_fingerprint, policy_id,
                stage_number, status, requester_id, approver_id, approver_role,
                secondary_approver_id, secondary_approver_role, rejection_reason, issued_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                approval_id, tenant_id, migration_id, intent_fingerprint, policy_id,
                stage_number, requester_id, approver_id, approver_role,
                secondary_approver_id, secondary_approver_role, issued_at, expires_at,
            ),
        )

    def get_approval(self, tenant_id: str, approval_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM governance_approvals WHERE tenant_id = ? AND approval_id = ?",
            (tenant_id, approval_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_active_approval_for_migration(self, tenant_id: str, migration_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM governance_approvals WHERE tenant_id = ? AND migration_id = ? AND status = 'APPROVED'",
            (tenant_id, migration_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def supersede_approvals_for_migration(self, tenant_id: str, migration_id: str) -> None:
        self.conn.execute(
            "UPDATE governance_approvals SET status = 'SUPERSEDED' WHERE tenant_id = ? AND migration_id = ? AND status = 'APPROVED'",
            (tenant_id, migration_id),
        )

    def revoke_approval(self, tenant_id: str, approval_id: str, reason: str = "Manually revoked") -> None:
        self.conn.execute(
            "UPDATE governance_approvals SET status = 'REVOKED', rejection_reason = ? WHERE tenant_id = ? AND approval_id = ?",
            (reason, tenant_id, approval_id),
        )


# ===========================================================================
# Keyring & Security Audit Repositories
# ===========================================================================

class SQLiteKeyringRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save_key(
        self,
        key_id: str,
        purpose: str,
        algorithm: str,
        public_key_pem: Optional[str],
        encrypted_private_key_blob: Optional[bytes],
        status: str = "ACTIVE",
        version: int = 1,
        created_at: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO security_keyring (
                key_id, purpose, algorithm, public_key_pem, encrypted_private_key_blob, status, version, created_at, retired_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (key_id, purpose, algorithm, public_key_pem, encrypted_private_key_blob, status, version, created_at),
        )

    def get_active_key(self, purpose: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM security_keyring WHERE purpose = ? AND status = 'ACTIVE' ORDER BY version DESC LIMIT 1",
            (purpose,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_key_by_id(self, key_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM security_keyring WHERE key_id = ?", (key_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    get_key = get_key_by_id

    def retire_key(self, key_id: str, retired_at: str) -> None:
        self.conn.execute(
            "UPDATE security_keyring SET status = 'RETIRED', retired_at = ? WHERE key_id = ?",
            (retired_at, key_id),
        )

    def revoke_key(self, key_id: str, retired_at: str) -> None:
        self.conn.execute(
            "UPDATE security_keyring SET status = 'REVOKED', retired_at = ? WHERE key_id = ?",
            (retired_at, key_id),
        )


class SQLiteSecurityAuditRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_latest_sequence_and_hash(self, tenant_id: str) -> Tuple[int, str]:
        cur = self.conn.execute(
            "SELECT sequence_number, entry_hash FROM security_audit_ledger WHERE tenant_id = ? ORDER BY sequence_number DESC LIMIT 1",
            (tenant_id,),
        )
        row = cur.fetchone()
        if row is None:
            return 0, "0000000000000000000000000000000000000000000000000000000000000000"
        return row["sequence_number"], row["entry_hash"]

    def append_entry(
        self,
        audit_id: str,
        tenant_id: str,
        sequence_number: int,
        actor_id: str,
        actor_type: str,
        event_type: str,
        resource_type: str,
        resource_id: str,
        action: str,
        decision: str,
        details: Dict[str, Any],
        previous_hash: str,
        entry_hash: str,
        timestamp: str,
        signature: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO security_audit_ledger (
                audit_id, tenant_id, sequence_number, actor_id, actor_type, event_type,
                resource_type, resource_id, action, decision, details, previous_hash, entry_hash, signature, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id, tenant_id, sequence_number, actor_id, actor_type, event_type,
                resource_type, resource_id, action, decision, json.dumps(details), previous_hash, entry_hash, signature, timestamp
            ),
        )

    def list_entries(self, tenant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM security_audit_ledger WHERE tenant_id = ? ORDER BY sequence_number ASC LIMIT ?",
            (tenant_id, limit),
        )
        rows = cur.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["details"] = json.loads(d["details"])
            results.append(d)
        return results
