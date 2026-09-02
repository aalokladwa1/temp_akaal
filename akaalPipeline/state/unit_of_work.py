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
from akaalPipeline.state.repositories import (
    SQLiteABACPolicyRepository,
    SQLiteCredentialRepository,
    SQLiteGovernanceApprovalRepository,
    SQLiteGroupRepository,
    SQLiteKeyringRepository,
    SQLiteMFARepository,
    SQLiteMigrationRepository,
    SQLitePrincipalRepository,
    SQLiteProjectRepository,
    SQLiteRoleGrantRepository,
    SQLiteRolePermissionRepository,
    SQLiteRoleRepository,
    SQLiteSCIMMappingRepository,
    SQLiteSecurityAuditRepository,
    SQLiteServiceTokenRepository,
    SQLiteSessionRepository,
    SQLiteTenantRepository,
    SQLiteWorkspaceRepository,
)


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

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_conn()

    def initialize_schema(self) -> None:
        self._init_all_tables()

    @property
    def tenants(self) -> SQLiteTenantRepository:
        return SQLiteTenantRepository(self._get_conn())

    @property
    def workspaces(self) -> SQLiteWorkspaceRepository:
        return SQLiteWorkspaceRepository(self._get_conn())

    @property
    def projects(self) -> SQLiteProjectRepository:
        return SQLiteProjectRepository(self._get_conn())

    @property
    def principals(self) -> SQLitePrincipalRepository:
        return SQLitePrincipalRepository(self._get_conn())

    @property
    def credentials(self) -> SQLiteCredentialRepository:
        return SQLiteCredentialRepository(self._get_conn())

    @property
    def sessions(self) -> SQLiteSessionRepository:
        return SQLiteSessionRepository(self._get_conn())

    @property
    def service_tokens(self) -> SQLiteServiceTokenRepository:
        return SQLiteServiceTokenRepository(self._get_conn())

    @property
    def groups(self) -> SQLiteGroupRepository:
        return SQLiteGroupRepository(self._get_conn())

    @property
    def roles(self) -> SQLiteRoleRepository:
        return SQLiteRoleRepository(self._get_conn())

    @property
    def role_permissions(self) -> SQLiteRolePermissionRepository:
        return SQLiteRolePermissionRepository(self._get_conn())

    @property
    def role_grants(self) -> SQLiteRoleGrantRepository:
        return SQLiteRoleGrantRepository(self._get_conn())

    @property
    def abac_policies(self) -> SQLiteABACPolicyRepository:
        return SQLiteABACPolicyRepository(self._get_conn())

    @property
    def governance_approvals(self) -> SQLiteGovernanceApprovalRepository:
        return SQLiteGovernanceApprovalRepository(self._get_conn())

    @property
    def keyring(self) -> SQLiteKeyringRepository:
        return SQLiteKeyringRepository(self._get_conn())

    @property
    def audit_ledger(self) -> SQLiteSecurityAuditRepository:
        return SQLiteSecurityAuditRepository(self._get_conn())

    @property
    def mfa(self) -> SQLiteMFARepository:
        return SQLiteMFARepository(self._get_conn())

    @property
    def scim_mappings(self) -> SQLiteSCIMMappingRepository:
        return SQLiteSCIMMappingRepository(self._get_conn())

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
                principal_type TEXT NOT NULL CHECK(principal_type IN ('HUMAN', 'SERVICE', 'MACHINE', 'WORKLOAD', 'SYSTEM')),
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
                authentication_assurance TEXT NOT NULL DEFAULT 'NONE',
                credential_mechanism TEXT,
                trust_domain TEXT,
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
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT,
                migration_id TEXT NOT NULL,
                operation_type TEXT NOT NULL DEFAULT 'migration.start',
                schedule_type TEXT NOT NULL DEFAULT 'RECURRING',
                cron_expression TEXT NOT NULL,
                one_shot_time TEXT,
                timezone TEXT NOT NULL DEFAULT 'UTC',
                state TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                revision INTEGER NOT NULL DEFAULT 1,
                misfire_policy TEXT NOT NULL DEFAULT 'SKIP',
                overlap_policy TEXT NOT NULL DEFAULT 'REJECT_OVERLAP',
                activation_id TEXT,
                creator_actor_id TEXT,
                delegated_roles TEXT,
                last_occurrence_time TEXT,
                next_occurrence_time TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schedule_occurrences (
                occurrence_id TEXT PRIMARY KEY,
                schedule_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT,
                schedule_revision INTEGER NOT NULL DEFAULT 1,
                canonical_scheduled_time TEXT NOT NULL,
                status TEXT NOT NULL,
                claim_attempt_id TEXT,
                claim_owner_id TEXT,
                lease_id TEXT,
                fence_epoch INTEGER NOT NULL DEFAULT 1,
                dispatched_at TEXT,
                dispatched_command_id TEXT,
                dispatched_operation_id TEXT,
                completed_at TEXT,
                result_summary TEXT,
                error_payload TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (schedule_id, schedule_revision, canonical_scheduled_time)
            );

            CREATE TABLE IF NOT EXISTS retention_operations (
                retention_op_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT,
                initiator_actor_id TEXT NOT NULL,
                is_preview INTEGER NOT NULL DEFAULT 0,
                cutoff_time TEXT NOT NULL,
                data_classes TEXT NOT NULL,
                status TEXT NOT NULL,
                considered_count INTEGER NOT NULL DEFAULT 0,
                eligible_count INTEGER NOT NULL DEFAULT 0,
                deleted_count INTEGER NOT NULL DEFAULT 0,
                protected_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0,
                protection_breakdown TEXT NOT NULL DEFAULT '{}',
                error_details TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
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

            CREATE TABLE IF NOT EXISTS capacity_observations (
                observation_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT,
                node_id TEXT,
                resource_type TEXT NOT NULL,
                value REAL NOT NULL,
                units TEXT NOT NULL,
                evidence_kind TEXT NOT NULL,
                source_authority TEXT NOT NULL,
                freshness_sec REAL NOT NULL DEFAULT 0.0,
                provenance TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS capacity_forecasts (
                forecast_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                workspace_id TEXT NOT NULL DEFAULT 'default-workspace',
                project_id TEXT,
                resource_type TEXT NOT NULL,
                target_metric TEXT NOT NULL,
                current_value REAL NOT NULL,
                growth_rate_per_sec REAL NOT NULL,
                projected_exhaustion_time TEXT,
                sample_count INTEGER NOT NULL,
                observation_window_sec REAL NOT NULL,
                evidence_kind TEXT NOT NULL,
                confidence_score REAL,
                assumptions TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alert_rules (
                rule_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                name TEXT NOT NULL,
                signal_name TEXT NOT NULL,
                operator TEXT NOT NULL,
                threshold_value TEXT NOT NULL,
                threshold_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                dedup_window_sec INTEGER NOT NULL DEFAULT 300,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                rule_id TEXT,
                signal_name TEXT NOT NULL,
                dedup_fingerprint TEXT NOT NULL,
                severity TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                message TEXT NOT NULL,
                current_value TEXT,
                threshold_value TEXT,
                context_payload TEXT,
                observation_count INTEGER NOT NULL DEFAULT 1,
                suppression_expires_at TEXT,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                resolved_at TEXT,
                first_observed_at TEXT NOT NULL,
                last_observed_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                migration_id TEXT,
                node_id TEXT,
                correlation_key TEXT,
                owner_actor_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT
            );

            CREATE TABLE IF NOT EXISTS incident_timeline (
                event_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS incident_alert_links (
                incident_id TEXT NOT NULL,
                alert_id TEXT NOT NULL,
                attached_at TEXT NOT NULL,
                PRIMARY KEY (incident_id, alert_id)
            );

            -- =========================================================
            -- P7.5 MFA + SCIM Identity Lifecycle Tables
            -- =========================================================
            CREATE TABLE IF NOT EXISTS mfa_factors (
                factor_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                factor_type TEXT NOT NULL CHECK(factor_type IN ('TOTP')),
                encrypted_secret_blob BLOB NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('PENDING_ACTIVATION', 'ACTIVE', 'DISABLED')),
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                PRIMARY KEY (tenant_id, factor_id),
                FOREIGN KEY (tenant_id, principal_id) REFERENCES enterprise_principals(tenant_id, principal_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS mfa_challenges (
                challenge_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                factor_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (tenant_id, challenge_id)
            );

            CREATE TABLE IF NOT EXISTS scim_provider_mappings (
                tenant_id TEXT NOT NULL,
                scim_provider_id TEXT NOT NULL,
                scim_external_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                last_synced_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, scim_provider_id, scim_external_id)
            );

            CREATE TABLE IF NOT EXISTS notification_deliveries (
                delivery_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default-tenant',
                alert_id TEXT,
                incident_id TEXT,
                channel TEXT NOT NULL,
                recipient TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                payload_fingerprint TEXT NOT NULL,
                idempotency_token TEXT NOT NULL,
                last_error TEXT,
                last_attempt_at TEXT,
                sent_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Migration columns if missing
        cols = [r[1] for r in conn.execute("PRAGMA table_info(migrations);").fetchall()]
        if "active_fence_epoch" not in cols:
            conn.execute("ALTER TABLE migrations ADD COLUMN active_fence_epoch INTEGER NOT NULL DEFAULT 1;")

        # Session assurance columns if missing (verified-authentication-assurance bridge)
        sess_cols = [r[1] for r in conn.execute("PRAGMA table_info(enterprise_sessions);").fetchall()]
        if "authentication_assurance" not in sess_cols:
            conn.execute("ALTER TABLE enterprise_sessions ADD COLUMN authentication_assurance TEXT NOT NULL DEFAULT 'NONE';")
        if "credential_mechanism" not in sess_cols:
            conn.execute("ALTER TABLE enterprise_sessions ADD COLUMN credential_mechanism TEXT;")
        if "trust_domain" not in sess_cols:
            conn.execute("ALTER TABLE enterprise_sessions ADD COLUMN trust_domain TEXT;")

        # Schedules columns if missing
        sched_cols = [r[1] for r in conn.execute("PRAGMA table_info(schedules);").fetchall()]
        if "workspace_id" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'default-workspace';")
        if "project_id" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN project_id TEXT;")
        if "operation_type" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN operation_type TEXT NOT NULL DEFAULT 'migration.start';")
        if "schedule_type" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN schedule_type TEXT NOT NULL DEFAULT 'RECURRING';")
        if "one_shot_time" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN one_shot_time TEXT;")
        if "timezone" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC';")
        if "enabled" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1;")
        if "revision" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;")
        if "misfire_policy" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN misfire_policy TEXT NOT NULL DEFAULT 'SKIP';")
        if "overlap_policy" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN overlap_policy TEXT NOT NULL DEFAULT 'REJECT_OVERLAP';")
        if "creator_actor_id" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN creator_actor_id TEXT;")
        if "delegated_roles" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN delegated_roles TEXT;")
        if "last_occurrence_time" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN last_occurrence_time TEXT;")
        if "next_occurrence_time" not in sched_cols:
            conn.execute("ALTER TABLE schedules ADD COLUMN next_occurrence_time TEXT;")

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
