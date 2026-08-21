"""akaalPipeline.state.repositories
===================================
Real durable persistence repository for pipeline canonical aggregates.
"""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from typing import Any, List, Optional
from akaalPipeline.contracts.errors import PersistenceError, RevisionConflictError
from akaalPipeline.state.aggregates import MigrationAggregate
from akaalPipeline.state.history import LifecycleHistoryRecord


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
        self._init_schema()


    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)

        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
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
            """)

    def save(self, aggregate: MigrationAggregate, connection: Optional[sqlite3.Connection] = None) -> None:
        owns_conn = False
        conn = connection
        if conn is None:
            conn = self._get_connection()
            owns_conn = True

        try:
            # Optimistic concurrency check if aggregate exists
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
