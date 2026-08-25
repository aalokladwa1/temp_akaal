"""akaalPipeline.state.unit_of_work
=================================
Real durable Unit of Work for atomic transactions across all motherboard tables.
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
            CREATE TABLE IF NOT EXISTS migrations (
                migration_id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL,
                name TEXT NOT NULL,
                mode TEXT NOT NULL,
                state TEXT NOT NULL,
                tenant_id TEXT,
                workspace_id TEXT,
                project_id TEXT,
                configuration TEXT NOT NULL,
                plan_id TEXT,
                initialization_id TEXT,
                active_attempt_id TEXT,
                active_schedule_id TEXT,
                lineage TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS lifecycle_history (
                history_id TEXT PRIMARY KEY,
                migration_id TEXT NOT NULL,
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
                artifact_type TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS operation_journal (
                operation_id TEXT PRIMARY KEY,
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
                migration_id TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                state TEXT NOT NULL,
                activation_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leases (
                lease_id TEXT PRIMARY KEY,
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
                attempt_id TEXT NOT NULL,
                invocation_id TEXT NOT NULL,
                lease_id TEXT NOT NULL,
                fence_epoch INTEGER NOT NULL,
                graph_node_id TEXT NOT NULL,
                initialization_fingerprint TEXT NOT NULL,
                binding_id TEXT NOT NULL,
                payload_reference TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outbox_events (
                event_id TEXT PRIMARY KEY,
                aggregate_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,  -- 'PENDING', 'PUBLISHED'
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_trail (
                audit_id TEXT PRIMARY KEY,
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

        # Idempotent schema migration for existing databases
        columns = [row[1] for row in conn.execute("PRAGMA table_info(node_executions);").fetchall()]
        if "current_engine_task_id" not in columns:
            conn.execute("ALTER TABLE node_executions ADD COLUMN current_engine_task_id TEXT;")



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
