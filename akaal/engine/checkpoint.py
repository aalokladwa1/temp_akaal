"""
AKAAL Engine Checkpoint Repository
===================================
Sub-millisecond atomic SQLite WAL checkpoint repository storing batch sequence
offsets, PK high-water-marks, and cryptographic batch digests.
"""

import os
import sqlite3
import threading
import logging
from typing import Dict, Any, List, Optional
from akaal.engine.spec import BatchState

logger = logging.getLogger("akaal.engine.checkpoint")


class CheckpointStore:
    """Process-safe, thread-safe atomic WAL checkpoint repository."""

    def __init__(self, db_path: Optional[str] = None, durability_mode: str = "NORMAL"):
        if db_path is None:
            db_dir = os.path.join(os.getcwd(), "artifacts")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "checkpoints.db")

        self.db_path = db_path
        self.durability_mode = durability_mode.upper()
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=60.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(f"PRAGMA synchronous={self.durability_mode};")
            conn.execute("PRAGMA busy_timeout=60000;")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                migration_id TEXT NOT NULL,
                partition_id TEXT NOT NULL,
                table_name TEXT NOT NULL,
                batch_number INTEGER NOT NULL,
                worker_id TEXT NOT NULL,
                rows_processed INTEGER NOT NULL,
                last_committed_key TEXT,
                checksum TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

    def begin_batch(self, checkpoint_id: str, migration_id: str, partition_id: str, table_name: str, batch_number: int, worker_id: str) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
            INSERT INTO checkpoints (
                checkpoint_id, migration_id, partition_id, table_name, batch_number,
                worker_id, rows_processed, checksum, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, '', 'IN_PROGRESS', DATETIME('now'), DATETIME('now'))
            ON CONFLICT(checkpoint_id) DO UPDATE SET
                status='IN_PROGRESS', updated_at=DATETIME('now')
            """, (checkpoint_id, migration_id, partition_id, table_name, batch_number, worker_id))

    def mark_batch_committed(
        self,
        checkpoint_id: str,
        migration_id: str,
        partition_id: str,
        table_name: str,
        batch_number: int,
        worker_id: str,
        rows_processed: int,
        last_committed_key: Optional[Any],
        checksum: str,
    ) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute("""
            INSERT INTO checkpoints (
                checkpoint_id, migration_id, partition_id, table_name, batch_number,
                worker_id, rows_processed, last_committed_key, checksum, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMMITTED', DATETIME('now'), DATETIME('now'))
            ON CONFLICT(checkpoint_id) DO UPDATE SET
                rows_processed=excluded.rows_processed,
                last_committed_key=excluded.last_committed_key,
                checksum=excluded.checksum,
                status='COMMITTED',
                updated_at=DATETIME('now')
            """, (
                checkpoint_id, migration_id, partition_id, table_name, batch_number,
                worker_id, rows_processed, str(last_committed_key) if last_committed_key is not None else None, checksum
            ))

    def get_latest_checkpoint(self, partition_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM checkpoints WHERE partition_id=? AND status='COMMITTED' ORDER BY batch_number DESC LIMIT 1",
            (partition_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def list_checkpoints_for_migration(self, migration_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM checkpoints WHERE migration_id=? ORDER BY batch_number ASC", (migration_id,))
        return [dict(r) for r in cur.fetchall()]
