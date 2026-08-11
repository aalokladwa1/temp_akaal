"""
AKAAL Engine State Repository
==============================
SQLite WAL-backed transactional storage for migration_state,
partition_state, batch_state, and attempt_log.
"""

import os
import sqlite3
import threading
import logging
from typing import Dict, Any, List, Optional
from akaal.engine.spec import MigrationState, PartitionState, BatchState

logger = logging.getLogger("akaal.engine.state")


class EngineStateRepository:
    """Thread-safe SQLite WAL repository for migration lifecycle state."""

    def __init__(self, db_path: Optional[str] = None, durability_mode: str = "NORMAL"):
        if db_path is None:
            db_dir = os.path.join(os.getcwd(), "artifacts")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "state.db")

        self.db_path = db_path
        self.durability_mode = durability_mode.upper()
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            conn.execute(f"PRAGMA journal_mode=WAL;")
            conn.execute(f"PRAGMA synchronous={self.durability_mode};")
            conn.execute(f"PRAGMA busy_timeout=10000;")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS migration_state (
                migration_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                spec_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS partition_state (
                partition_id TEXT PRIMARY KEY,
                migration_id TEXT NOT NULL,
                table_name TEXT NOT NULL,
                schema_name TEXT NOT NULL,
                strategy TEXT NOT NULL,
                lower_bound TEXT,
                upper_bound TEXT,
                last_committed_source_key TEXT,
                last_committed_batch_sequence INTEGER DEFAULT 0,
                committed_rows INTEGER DEFAULT 0,
                last_batch_id TEXT,
                state TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS batch_state (
                batch_id TEXT PRIMARY KEY,
                partition_id TEXT NOT NULL,
                migration_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                row_count INTEGER NOT NULL,
                first_pk TEXT,
                last_pk TEXT,
                checksum TEXT,
                state TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS attempt_log (
                attempt_id TEXT PRIMARY KEY,
                migration_id TEXT NOT NULL,
                partition_id TEXT,
                worker_id TEXT,
                error_type TEXT,
                stack_trace TEXT,
                logged_at TEXT NOT NULL
            )
            """)

    def set_migration_state(self, migration_id: str, state: MigrationState, spec_json: Optional[str] = None) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
            INSERT INTO migration_state (migration_id, state, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, DATETIME('now'), DATETIME('now'))
            ON CONFLICT(migration_id) DO UPDATE SET
                state=excluded.state,
                spec_json=COALESCE(excluded.spec_json, migration_state.spec_json),
                updated_at=DATETIME('now')
            """, (migration_id, state.value, spec_json))

    def get_migration_state(self, migration_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT migration_id, state, spec_json, created_at, updated_at FROM migration_state WHERE migration_id=?", (migration_id,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def set_partition_state(
        self,
        partition_id: str,
        migration_id: str,
        table_name: str,
        schema_name: str,
        strategy: str,
        state: PartitionState,
        lower_bound: Optional[Any] = None,
        upper_bound: Optional[Any] = None,
        last_committed_source_key: Optional[Any] = None,
        committed_rows: int = 0,
        last_batch_id: Optional[str] = None,
    ) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
            INSERT INTO partition_state (
                partition_id, migration_id, table_name, schema_name, strategy,
                lower_bound, upper_bound, last_committed_source_key, committed_rows, last_batch_id, state, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATETIME('now'))
            ON CONFLICT(partition_id) DO UPDATE SET
                last_committed_source_key=COALESCE(excluded.last_committed_source_key, partition_state.last_committed_source_key),
                committed_rows=excluded.committed_rows,
                last_batch_id=COALESCE(excluded.last_batch_id, partition_state.last_batch_id),
                state=excluded.state,
                updated_at=DATETIME('now')
            """, (
                partition_id, migration_id, table_name, schema_name, strategy,
                str(lower_bound) if lower_bound is not None else None,
                str(upper_bound) if upper_bound is not None else None,
                str(last_committed_source_key) if last_committed_source_key is not None else None,
                committed_rows, last_batch_id, state.value
            ))

    def get_partition_state(self, partition_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM partition_state WHERE partition_id=?", (partition_id,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def list_partitions_for_migration(self, migration_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM partition_state WHERE migration_id=?", (migration_id,))
        return [dict(r) for r in cur.fetchall()]

    def record_attempt(self, attempt_id: str, migration_id: str, partition_id: Optional[str], worker_id: Optional[str], error_type: str, stack_trace: str) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
            INSERT INTO attempt_log (attempt_id, migration_id, partition_id, worker_id, error_type, stack_trace, logged_at)
            VALUES (?, ?, ?, ?, ?, ?, DATETIME('now'))
            """, (attempt_id, migration_id, partition_id, worker_id, error_type, stack_trace))
