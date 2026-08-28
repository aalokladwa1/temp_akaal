"""akaalPipeline.state.unit_of_work
=================================
Real durable Unit of Work for atomic transactions across all motherboard & security tables.
"""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional
from akaalPipeline.contracts.errors import PersistenceError
from akaalPipeline.state.repositories import SQLiteMigrationRepository


class UnitOfWorkPort(ABC):
    @abstractmethod
    def __enter__(self) -> UnitOfWorkPort:
        """Begin transaction."""

    @abstractmethod
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Commit if clean, rollback on exception."""

    @abstractmethod
    def commit(self) -> None:
        """Commit transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Rollback transaction."""

    @property
    @abstractmethod
    def connection(self) -> sqlite3.Connection:
        """Access connection."""


class SQLiteUnitOfWork(UnitOfWorkPort):
    def __init__(self, db_path: Optional[str] = None, shared_connection: Optional[sqlite3.Connection] = None) -> None:
        if db_path is None and shared_connection is None:
            raise ValueError("SQLiteUnitOfWork requires an explicit db_path or shared_connection.")
        self.db_path = db_path or ":memory:"
        self._shared_conn = shared_connection
        self._conn: Optional[sqlite3.Connection] = None
        self._in_transaction = False
        self.repository = SQLiteMigrationRepository(db_path=self.db_path)
        self._init_all_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if self._shared_conn:
            return self._shared_conn
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    @property
    def connection(self) -> sqlite3.Connection:
        return self._get_conn()

    def _init_all_tables(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            -- =========================================================
            -- Hierarchy & Tenancy Tables
            -- =========================================================
            CREATE TABLE IF NOT EXISTS enterprise_tenants (
                tenant_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'SUSPENDED', 'DECOMMISSIONED')),
                security_revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS enterprise_workspaces (
                workspace_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'SUSPENDED')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, workspace_id),
                FOREIGN KEY (tenant_id) REFERENCES enterprise_tenants(tenant_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS enterprise_projects (
                project_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'SUSPENDED')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, workspace_id, project_id),
                FOREIGN KEY (tenant_id, workspace_id) REFERENCES enterprise_workspaces(tenant_id, workspace_id) ON DELETE RESTRICT
            );

            -- =========================================================
            -- Identity & Security Tables
            -- =========================================================
            CREATE TABLE IF NOT EXISTS enterprise_principals (
                principal_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                principal_type TEXT NOT NULL CHECK(principal_type IN ('HUMAN', 'SERVICE', 'MACHINE', 'SYSTEM')),
                username TEXT NOT NULL,
                display_name TEXT,
                email TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_locked INTEGER NOT NULL DEFAULT 0,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                security_revision INTEGER NOT NULL DEFAULT 1,
                metadata JSON NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, principal_id),
                UNIQUE (tenant_id, username),
                FOREIGN KEY (tenant_id) REFERENCES enterprise_tenants(tenant_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS principal_credentials (
                credential_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                kdf_algorithm TEXT NOT NULL CHECK(kdf_algorithm IN ('ARGON2ID', 'PBKDF2_SHA256')),
                kdf_params JSON NOT NULL,
                salt_hex TEXT NOT NULL,
                password_hash_hex TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, credential_id),
                FOREIGN KEY (tenant_id, principal_id) REFERENCES enterprise_principals(tenant_id, principal_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS enterprise_sessions (
                session_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                session_token_hash TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                last_activity_at TEXT NOT NULL,
                absolute_expires_at TEXT NOT NULL,
                idle_timeout_seconds INTEGER NOT NULL DEFAULT 1800,
                is_revoked INTEGER NOT NULL DEFAULT 0,
                revocation_reason TEXT,
                client_ip TEXT,
                user_agent TEXT,
                bound_security_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, session_id),
                FOREIGN KEY (tenant_id, principal_id) REFERENCES enterprise_principals(tenant_id, principal_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS service_api_tokens (
                token_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                token_prefix TEXT NOT NULL,
                name TEXT NOT NULL,
                scopes JSON NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT,
                is_revoked INTEGER NOT NULL DEFAULT 0,
                revoked_at TEXT,
                bound_security_revision INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, token_id),
                FOREIGN KEY (tenant_id, principal_id) REFERENCES enterprise_principals(tenant_id, principal_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS enterprise_groups (
                group_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, group_id),
                UNIQUE (tenant_id, name),
                FOREIGN KEY (tenant_id) REFERENCES enterprise_tenants(tenant_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS group_memberships (
                tenant_id TEXT NOT NULL,
                group_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                PRIMARY KEY (tenant_id, group_id, principal_id),
                FOREIGN KEY (tenant_id, group_id) REFERENCES enterprise_groups(tenant_id, group_id) ON DELETE CASCADE,
                FOREIGN KEY (tenant_id, principal_id) REFERENCES enterprise_principals(tenant_id, principal_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS enterprise_roles (
                role_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                is_builtin INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                parent_role_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, role_id),
                UNIQUE (tenant_id, name),
                FOREIGN KEY (tenant_id) REFERENCES enterprise_tenants(tenant_id) ON DELETE RESTRICT,
                FOREIGN KEY (tenant_id, parent_role_id) REFERENCES enterprise_roles(tenant_id, role_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS role_permissions (
                tenant_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                permission_id TEXT NOT NULL,
                PRIMARY KEY (tenant_id, role_id, permission_id),
                FOREIGN KEY (tenant_id, role_id) REFERENCES enterprise_roles(tenant_id, role_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS role_grants (
                grant_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                subject_type TEXT NOT NULL CHECK(subject_type IN ('PRINCIPAL', 'GROUP')),
                subject_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                resource_type TEXT NOT NULL CHECK(resource_type IN ('ORGANIZATION', 'WORKSPACE', 'PROJECT', 'MIGRATION', 'SYSTEM')),
                resource_id TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                expires_at TEXT,
                is_jit INTEGER NOT NULL DEFAULT 0,
                jit_purpose TEXT,
                is_revoked INTEGER NOT NULL DEFAULT 0,
                revoked_at TEXT,
                PRIMARY KEY (tenant_id, grant_id),
                FOREIGN KEY (tenant_id) REFERENCES enterprise_tenants(tenant_id) ON DELETE RESTRICT,
                FOREIGN KEY (tenant_id, role_id) REFERENCES enterprise_roles(tenant_id, role_id) ON DELETE CASCADE,
                FOREIGN KEY (tenant_id, granted_by) REFERENCES enterprise_principals(tenant_id, principal_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS abac_policies (
                policy_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                effect TEXT NOT NULL CHECK(effect IN ('ALLOW', 'DENY')),
                target_action TEXT NOT NULL,
                target_resource_type TEXT NOT NULL,
                condition_expression JSON NOT NULL,
                priority INTEGER NOT NULL DEFAULT 100,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, policy_id),
                FOREIGN KEY (tenant_id) REFERENCES enterprise_tenants(tenant_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS governance_approvals (
                approval_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                migration_id TEXT NOT NULL,
                intent_fingerprint TEXT NOT NULL,
                policy_id TEXT NOT NULL,
                stage_number INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED', 'REVOKED', 'EXPIRED', 'SUPERSEDED')),
                requester_id TEXT NOT NULL,
                approver_id TEXT,
                approver_role TEXT,
                secondary_approver_id TEXT,
                secondary_approver_role TEXT,
                rejection_reason TEXT,
                issued_at TEXT NOT NULL,
                expires_at TEXT,
                PRIMARY KEY (tenant_id, approval_id),
                FOREIGN KEY (tenant_id) REFERENCES enterprise_tenants(tenant_id) ON DELETE RESTRICT,
                FOREIGN KEY (tenant_id, requester_id) REFERENCES enterprise_principals(tenant_id, principal_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS security_keyring (
                key_id TEXT NOT NULL,
                purpose TEXT NOT NULL CHECK(purpose IN ('EXECUTION_SIGNING', 'AUDIT_SEAL', 'TOKEN_ENCRYPT', 'RECEIPT_SIGNING')),
                algorithm TEXT NOT NULL CHECK(algorithm IN ('ED25519', 'HMAC_SHA256', 'AES_256_GCM')),
                public_key_pem TEXT,
                encrypted_private_key_blob BLOB,
                status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'RETIRED', 'REVOKED')),
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                retired_at TEXT,
                PRIMARY KEY (key_id)
            );

            CREATE TABLE IF NOT EXISTS security_audit_ledger (
                audit_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                actor_id TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                event_type TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                action TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('ALLOW', 'DENY', 'MUTATE', 'LOGIN_SUCCESS', 'LOGIN_FAILURE')),
                details JSON NOT NULL,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL,
                signature TEXT,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (tenant_id, sequence_number),
                UNIQUE (audit_id)
            );

            -- =========================================================
            -- Canonical Motherboard Tables
            -- =========================================================
            CREATE TABLE IF NOT EXISTS migrations (
                migration_id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL,
                name TEXT NOT NULL,
                mode TEXT NOT NULL,
                state TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT,
                configuration TEXT NOT NULL,
                plan_id TEXT,
                initialization_id TEXT,
                active_attempt_id TEXT,
                active_schedule_id TEXT,
                active_fence_epoch INTEGER NOT NULL DEFAULT 1,
                lineage TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lifecycle_history (
                history_id TEXT PRIMARY KEY,
                migration_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                actor TEXT NOT NULL,
                reason TEXT NOT NULL,
                correlation_id TEXT,
                details TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS immutable_artifacts (
                artifact_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                artifact_type TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS operation_journal (
                operation_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                command_id TEXT NOT NULL,
                idempotency_key TEXT,
                status TEXT NOT NULL,
                actor TEXT NOT NULL,
                payload_fingerprint TEXT NOT NULL,
                result_payload TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS idempotency_records (
                record_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT,
                command_name TEXT NOT NULL DEFAULT 'command',
                command_id TEXT NOT NULL DEFAULT 'cmd',
                payload_fingerprint TEXT NOT NULL,
                result_payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schedules (
                schedule_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                migration_id TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                state TEXT NOT NULL,
                activation_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leases (
                lease_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                attempt_id TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                fence_epoch INTEGER NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                renewed_at TEXT NOT NULL,
                initialization_fingerprint TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT NOT NULL DEFAULT 'default-project',
                migration_id TEXT NOT NULL DEFAULT 'default-migration',
                execution_id TEXT NOT NULL DEFAULT 'default-exec',
                generation INTEGER NOT NULL DEFAULT 1,
                attempt_id TEXT NOT NULL,
                invocation_id TEXT NOT NULL,
                lease_id TEXT NOT NULL,
                fence_epoch INTEGER NOT NULL,
                graph_node_id TEXT NOT NULL,
                initialization_fingerprint TEXT NOT NULL,
                execution_seal_fingerprint TEXT NOT NULL DEFAULT '',
                security_revision INTEGER NOT NULL DEFAULT 1,
                source_identity_fp TEXT NOT NULL DEFAULT '',
                target_identity_fp TEXT NOT NULL DEFAULT '',
                binding_id TEXT NOT NULL,
                payload_reference TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outbox_events (
                event_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                aggregate_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_trail (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                correlation_id TEXT,
                causation_id TEXT,
                evidence_fingerprint TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projection_views (
                view_name TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT NOT NULL DEFAULT '',
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (view_name, entity_id, tenant_id, workspace_id, project_id)
            );

            CREATE TABLE IF NOT EXISTS plan_executions (
                execution_id TEXT PRIMARY KEY,
                migration_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                plan_fingerprint TEXT NOT NULL,
                initialization_fingerprint TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL,
                start_operation_id TEXT,
                checkpoint_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS node_executions (
                node_execution_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                migration_id TEXT NOT NULL,
                graph_node_id TEXT NOT NULL,
                capability_contract TEXT NOT NULL,
                side_effect TEXT NOT NULL,
                state TEXT NOT NULL,
                current_attempt_id TEXT,
                current_invocation_id TEXT,
                current_engine_task_id TEXT,
                binding_id TEXT,
                contract_version TEXT,
                lease_id TEXT,
                fence_epoch INTEGER,
                checkpoint_id TEXT,
                result_payload TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (execution_id, graph_node_id)
            );
        """)

        # Migration columns if missing
        cols = [r[1] for r in conn.execute("PRAGMA table_info(migrations);").fetchall()]
        if "active_fence_epoch" not in cols:
            conn.execute("ALTER TABLE migrations ADD COLUMN active_fence_epoch INTEGER NOT NULL DEFAULT 1;")

        if not self._shared_conn:
            conn.commit()

    def __enter__(self) -> SQLiteUnitOfWork:
        conn = self._get_conn()
        conn.execute("BEGIN IMMEDIATE;")
        self._in_transaction = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            if self._in_transaction:
                self.commit()

    def commit(self) -> None:
        if self._in_transaction and self._conn:
            try:
                self._conn.commit()
            except sqlite3.Error as err:
                self.rollback()
                raise PersistenceError("Error committing transaction", cause=err) from err
            finally:
                self._in_transaction = False

    def rollback(self) -> None:
        if self._in_transaction and self._conn:
            try:
                self._conn.rollback()
            except sqlite3.Error:
                pass
            finally:
                self._in_transaction = False

    def close(self) -> None:
        if self._conn and not self._shared_conn:
            self._conn.close()
            self._conn = None
