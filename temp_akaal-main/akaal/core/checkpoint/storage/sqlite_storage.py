"""
Akaal — SQLite Checkpoint Storage Adapter
==========================================
Persists checkpoints to an SQLite database file.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.storage.base_storage import ICheckpointStorageAdapter
from akaal.core.models.enums import WorkflowState

logger = logging.getLogger("akaal.core.checkpoint.storage.sqlite")


class SQLiteCheckpointStorageAdapter(ICheckpointStorageAdapter):
    """
    SQLite backend for persisting CheckpointRecords.
    Automatically initializes table definitions and indexes if they do not exist.
    """

    def __init__(self, db_path: str) -> None:
        """
        Initialize the SQLite adapter.
        Args:
            db_path: Absolute or relative path to the SQLite database file.
        """
        self.db_path = db_path
        logger.debug("[SQLiteStorage] Initialized with DB path: %s", db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection to SQLite database."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    async def initialize(self) -> None:
        """Creates the checkpoints table and indexes if they do not exist."""
        def _init():
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("PRAGMA journal_mode=WAL;")
                except Exception as e:
                    logger.debug("[SQLiteStorage] Failed to set WAL mode: %s", e)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        checkpoint_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        migration_id TEXT NOT NULL,
                        workflow_state TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        batch_number INTEGER NOT NULL,
                        worker_id TEXT NOT NULL,
                        last_processed_primary_key TEXT,
                        rows_processed INTEGER NOT NULL,
                        rows_failed INTEGER NOT NULL,
                        rows_skipped INTEGER NOT NULL,
                        retry_count INTEGER NOT NULL,
                        adapter_state TEXT,
                        metrics TEXT,
                        checksum TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        status TEXT NOT NULL
                    )
                """)
                
                # Indexes to optimize resume lookups and list operations
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_proj_mig 
                    ON checkpoints (project_id, migration_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_proj_mig_tbl 
                    ON checkpoints (project_id, migration_id, table_name)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_checkpoints_status 
                    ON checkpoints (status)
                """)
                
                conn.commit()
                logger.info("[SQLiteStorage] Database initialized and tables verified at %s", self.db_path)
            except Exception as e:
                logger.critical("[SQLiteStorage] Initialization failed: %s", e, exc_info=True)
                raise RuntimeError(f"Failed to initialize SQLite checkpoint storage: {e}") from e
            finally:
                if conn:
                    conn.close()

        await asyncio.to_thread(_init)

    async def write(self, record: CheckpointRecord) -> bool:
        """Upsert a CheckpointRecord in SQLite database."""
        if not record:
            logger.warning("[SQLiteStorage] Attempted to write empty record.")
            return False

        def _write():
            conn = None
            try:
                record.updated_at = datetime.now(timezone.utc).isoformat()
                record.checksum = record.calculate_checksum()
                if record.status == CheckpointStatus.PENDING:
                    record.status = CheckpointStatus.COMMITTED

                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Serialize Dict PK to JSON string for SQLite storage
                serialized_pk = None
                if record.last_processed_primary_key is not None:
                    serialized_pk = json.dumps(record.last_processed_primary_key)

                cursor.execute("""
                    INSERT OR REPLACE INTO checkpoints (
                        checkpoint_id, project_id, migration_id, workflow_state,
                        table_name, batch_number, worker_id, last_processed_primary_key,
                        rows_processed, rows_failed, rows_skipped, retry_count,
                        adapter_state, metrics, checksum, created_at, updated_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.checkpoint_id,
                    record.project_id,
                    record.migration_id,
                    record.workflow_state.value,
                    record.table_name,
                    record.batch_number,
                    record.worker_id,
                    serialized_pk,
                    record.rows_processed,
                    record.rows_failed,
                    record.rows_skipped,
                    record.retry_count,
                    json.dumps(record.adapter_state),
                    json.dumps(record.metrics),
                    record.checksum,
                    record.created_at,
                    record.updated_at,
                    record.status.value
                ))
                conn.commit()
                logger.debug("[SQLiteStorage] Checkpoint %s committed to database.", record.checkpoint_id)
                return True
            except Exception as e:
                logger.error("[SQLiteStorage] Write failed for checkpoint %s: %s", record.checkpoint_id, e, exc_info=True)
                return False
            finally:
                if conn:
                    conn.close()

        return await asyncio.to_thread(_write)

    async def read(self, checkpoint_id: str) -> Optional[CheckpointRecord]:
        """Read a CheckpointRecord from SQLite."""
        def _read():
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_record(row)
            except Exception as e:
                logger.error("[SQLiteStorage] Read failed for checkpoint %s: %s", checkpoint_id, e, exc_info=True)
                return None
            finally:
                if conn:
                    conn.close()

        return await asyncio.to_thread(_read)

    async def read_latest(
        self, project_id: str, migration_id: str, table_name: Optional[str] = None
    ) -> Optional[CheckpointRecord]:
        """Read the latest matching CheckpointRecord based on updated_at/created_at fields."""
        def _read_latest():
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                if table_name:
                    cursor.execute("""
                        SELECT * FROM checkpoints 
                        WHERE project_id = ? AND migration_id = ? AND table_name = ?
                        ORDER BY updated_at DESC, created_at DESC LIMIT 1
                    """, (project_id, migration_id, table_name))
                else:
                    cursor.execute("""
                        SELECT * FROM checkpoints 
                        WHERE project_id = ? AND migration_id = ?
                        ORDER BY updated_at DESC, created_at DESC LIMIT 1
                    """, (project_id, migration_id))
                
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_record(row)
            except Exception as e:
                logger.error("[SQLiteStorage] Read latest failed: %s", e, exc_info=True)
                return None
            finally:
                if conn:
                    conn.close()

        return await asyncio.to_thread(_read_latest)

    async def list_by_migration(
        self, project_id: str, migration_id: str
    ) -> List[CheckpointRecord]:
        """List checkpoints by migration in chronological order."""
        def _list():
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM checkpoints 
                    WHERE project_id = ? AND migration_id = ? 
                    ORDER BY created_at ASC
                """, (project_id, migration_id))
                
                rows = cursor.fetchall()
                return [self._row_to_record(row) for row in rows]
            except Exception as e:
                logger.error("[SQLiteStorage] List checkpoints failed: %s", e, exc_info=True)
                return []
            finally:
                if conn:
                    conn.close()

        return await asyncio.to_thread(_list)

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint by ID."""
        def _delete():
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,))
                conn.commit()
                success = cursor.rowcount > 0
                return success
            except Exception as e:
                logger.error("[SQLiteStorage] Delete failed for checkpoint %s: %s", checkpoint_id, e, exc_info=True)
                return False
            finally:
                if conn:
                    conn.close()

        return await asyncio.to_thread(_delete)

    async def clear_migration(self, project_id: str, migration_id: str) -> int:
        """Clear all checkpoints belonging to migration_id."""
        def _clear():
            conn = None
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM checkpoints WHERE project_id = ? AND migration_id = ?", (project_id, migration_id))
                conn.commit()
                deleted_count = cursor.rowcount
                logger.info("[SQLiteStorage] Cleared %d checkpoints for migration %s", deleted_count, migration_id)
                return deleted_count
            except Exception as e:
                logger.error("[SQLiteStorage] Clear migration failed: %s", e, exc_info=True)
                return 0
            finally:
                if conn:
                    conn.close()

        return await asyncio.to_thread(_clear)

    def _row_to_record(self, row: sqlite3.Row) -> CheckpointRecord:
        """Map SQLite row columns to CheckpointRecord dataclass."""
        pk_val = row["last_processed_primary_key"]
        pk_dict = None
        if pk_val:
            try:
                pk_dict = json.loads(pk_val)
            except json.JSONDecodeError:
                # Handle fallback cases
                pk_dict = {"legacy_offset": pk_val}

        return CheckpointRecord(
            checkpoint_id=row["checkpoint_id"],
            project_id=row["project_id"],
            migration_id=row["migration_id"],
            workflow_state=WorkflowState(row["workflow_state"]),
            table_name=row["table_name"],
            batch_number=row["batch_number"],
            worker_id=row["worker_id"],
            last_processed_primary_key=pk_dict,
            rows_processed=row["rows_processed"],
            rows_failed=row["rows_failed"],
            rows_skipped=row["rows_skipped"],
            retry_count=row["retry_count"],
            adapter_state=json.loads(row["adapter_state"]) if row["adapter_state"] else {},
            metrics=json.loads(row["metrics"]) if row["metrics"] else {},
            checksum=row["checksum"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status=CheckpointStatus(row["status"])
        )
