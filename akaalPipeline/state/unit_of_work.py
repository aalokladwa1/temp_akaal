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
                idempotency_key TEXT PRIMARY KEY,
                command_id TEXT NOT NULL,
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
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (view_name, entity_id)
            );
        """)
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
