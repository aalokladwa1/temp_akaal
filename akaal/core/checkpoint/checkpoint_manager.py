"""
Akaal — Checkpoint Manager
===========================
Orchestrates progress tracking and recovery by coordinating storage adapters.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.storage.base_storage import ICheckpointStorageAdapter
from akaal.core.models.enums import WorkflowState

logger = logging.getLogger("akaal.core.checkpoint.manager")


class CheckpointManager:
    """
    Coordinates checkpoint creation, loading, validation, and resumption.
    Acts as a gateway interface between migration logic and storage backends.
    """

    def __init__(self, storage_adapter: ICheckpointStorageAdapter, metrics_registry: Optional[Any] = None) -> None:
        """
        Initialize the CheckpointManager with a storage adapter dependency.
        Args:
            storage_adapter: An implementation of ICheckpointStorageAdapter.
            metrics_registry: Optional MetricsRegistry instance.
        """
        if not storage_adapter:
            raise ValueError("A valid storage_adapter is required. Received: None.")
        self.storage = storage_adapter
        self._metrics = metrics_registry
        logger.debug("[CheckpointManager] Instantiated with storage adapter: %s", storage_adapter.__class__.__name__)

    async def save_progress(self, record: CheckpointRecord) -> bool:
        """
        Save the progress of an active migration batch.
        Calculates the checksum to guarantee data integrity and persists it.
        Args:
            record: The CheckpointRecord to persist.
        Returns:
            bool: True if save succeeded, False otherwise.
        """
        if not record:
            raise ValueError("Cannot save a None or empty record.")
        
        # Defensive Type Validation
        if record.last_processed_primary_key is not None and not isinstance(record.last_processed_primary_key, dict):
            raise TypeError(
                f"last_processed_primary_key must be a Dictionary or None. "
                f"Received type: {type(record.last_processed_primary_key).__name__}"
            )

        logger.debug(
            "[CheckpointManager] Saving progress: project=%s migration=%s table=%s batch=%d",
            record.project_id, record.migration_id, record.table_name, record.batch_number
        )
        try:
            success = await self.storage.write(record)
            if success:
                logger.debug("Checkpoint saved", extra={"event": "checkpoint_saved", "table_name": record.table_name})
                try:
                    if self._metrics is not None:
                        self._metrics.counter("checkpoint_save_count").increment()
                except Exception:
                    pass
            else:
                logger.error("Checkpoint failure", extra={"event": "checkpoint_failure", "table_name": record.table_name})
                try:
                    if self._metrics is not None:
                        self._metrics.counter("checkpoint_save_failure_count").increment()
                except Exception:
                    pass
            return success
        except Exception as e:
            logger.error("Checkpoint failure", extra={"event": "checkpoint_failure", "table_name": record.table_name})
            try:
                if self._metrics is not None:
                    self._metrics.counter("checkpoint_save_failure_count").increment()
            except Exception:
                pass
            raise

    async def load_progress(self, checkpoint_id: str) -> Optional[CheckpointRecord]:
        """
        Load a specific checkpoint and verify its checksum integrity.
        Args:
            checkpoint_id: Unique checkpoint GUID.
        Returns:
            Optional[CheckpointRecord]: The validated record, or None if not found.
        Raises:
            ValueError: If the checkpoint data fails checksum validation (corruption) or ID is empty.
        """
        if not checkpoint_id or not checkpoint_id.strip():
            raise ValueError("checkpoint_id must be a non-empty string.")

        record = await self.storage.read(checkpoint_id)
        if not record:
            logger.debug("[CheckpointManager] Checkpoint %s not found in storage.", checkpoint_id)
            return None

        # Verify checksum to ensure data was not tampered with or corrupted on disk
        if not record.verify_integrity():
            record.status = CheckpointStatus.CORRUPT
            raise ValueError(f"CHECKPOINT CORRUPTION: Checksum verification failed for checkpoint {checkpoint_id}.")

        return record

    async def resume(self, project_id: str, migration_id: str, table_name: str) -> Optional[CheckpointRecord]:
        """
        Retrieve the latest valid checkpoint for a specific table in a migration session.
        Args:
            project_id: Project identifier.
            migration_id: Migration session identifier.
            table_name: Database table name.
        Returns:
            Optional[CheckpointRecord]: The latest valid record matching the criteria, or None.
        Raises:
            ValueError: If the retrieved latest checkpoint fails checksum validation.
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id must be a non-empty string.")
        if not migration_id or not migration_id.strip():
            raise ValueError("migration_id must be a non-empty string.")
        if table_name is None:
            table_name = ""

        logger.info(
            "[CheckpointManager] Querying resume state for project=%s migration=%s table=%s",
            project_id, migration_id, table_name
        )
        record = await self.storage.read_latest(project_id, migration_id, table_name)
        if not record:
            logger.debug("[CheckpointManager] No previous checkpoint found to resume table %s.", table_name)
            return None

        if not record.verify_integrity():
            record.status = CheckpointStatus.CORRUPT
            logger.error("Checkpoint failure", extra={"event": "checkpoint_failure", "table_name": table_name})
            try:
                if self._metrics is not None:
                    self._metrics.counter("checkpoint_corruption_count").increment()
            except Exception:
                pass
            raise ValueError(
                f"CHECKPOINT CORRUPTION: Checksum mismatch on latest checkpoint {record.checkpoint_id} for table {table_name}."
            )

        logger.info("Checkpoint resumed", extra={"event": "checkpoint_resumed", "table_name": table_name})
        try:
            if self._metrics is not None:
                self._metrics.counter("checkpoint_resume_count").increment()
        except Exception:
            pass
        return record

    async def list_checkpoints(self, project_id: str, migration_id: str) -> List[CheckpointRecord]:
        """
        List all checkpoints for a migration run, sorted chronologically.
        Args:
            project_id: Project identifier.
            migration_id: Migration session identifier.
        Returns:
            List[CheckpointRecord]: Chronological list of checkpoints.
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id must be a non-empty string.")
        if not migration_id or not migration_id.strip():
            raise ValueError("migration_id must be a non-empty string.")
        return await self.storage.list_by_migration(project_id, migration_id)

    async def mark_completed(
        self,
        project_id: str,
        migration_id: str,
        table_name: str,
        worker_id: Optional[str] = "default",
        workflow_state: WorkflowState = WorkflowState.PRODUCTION_MIGRATION
    ) -> CheckpointRecord:
        """
        Save a terminal checkpoint marking a table's migration run as successfully completed.
        Args:
            project_id: Project identifier.
            migration_id: Migration session identifier.
            table_name: Table that has completed migration.
            worker_id: ID of the worker executing the migration (defaults to "default").
            workflow_state: The current workflow step.
        Returns:
            CheckpointRecord: The created completion record.
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id must be a non-empty string.")
        if not migration_id or not migration_id.strip():
            raise ValueError("migration_id must be a non-empty string.")
        if not table_name or not table_name.strip():
            raise ValueError("table_name must be a non-empty string.")

        completion_record = CheckpointRecord(
            checkpoint_id=str(uuid.uuid4()),
            project_id=project_id,
            migration_id=migration_id,
            workflow_state=workflow_state,
            table_name=table_name,
            batch_number=-1,  # Special value denoting table completion
            worker_id=worker_id,
            last_processed_primary_key=None,
            rows_processed=0,
            rows_failed=0,
            rows_skipped=0,
            retry_count=0,
            status=CheckpointStatus.COMPLETED
        )
        
        logger.info("[CheckpointManager] Marking table %s as COMPLETED.", table_name)
        await self.save_progress(completion_record)
        return completion_record

    async def mark_failed(self, checkpoint_id: str, error_details: str) -> bool:
        """
        Mark an existing checkpoint as failed and store the error context.
        Args:
            checkpoint_id: GUID of the checkpoint.
            error_details: Error message or stack trace.
        Returns:
            bool: True if status updated successfully, False if checkpoint not found or database write failed.
        """
        if not checkpoint_id or not checkpoint_id.strip():
            raise ValueError("checkpoint_id must be a non-empty string.")
        if not error_details or not error_details.strip():
            raise ValueError("error_details must be a non-empty string.")

        record = await self.storage.read(checkpoint_id)
        if not record:
            logger.warning("[CheckpointManager] Checkpoint %s not found to mark as failed.", checkpoint_id)
            return False

        record.status = CheckpointStatus.FAILED
        record.metrics["error_details"] = error_details
        logger.warning("[CheckpointManager] Checkpoint %s marked as FAILED. Error: %s", checkpoint_id, error_details)
        return await self.storage.write(record)

    async def purge(self, project_id: str, migration_id: str, max_age_days: Optional[int] = None) -> int:
        """
        Purge checkpoints for a specific migration.
        Safety constraints:
          - NEVER deletes PENDING or COMMITTED checkpoints.
          - Only deletes FAILED or COMPLETED checkpoints.
          - If max_age_days is provided, only deletes records older than that retention window.
        Args:
            project_id: Project identifier.
            migration_id: Migration session identifier.
            max_age_days: Configure retention duration (only purge records older than N days).
        Returns:
            int: The number of deleted checkpoint entries.
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id must be a non-empty string.")
        if not migration_id or not migration_id.strip():
            raise ValueError("migration_id must be a non-empty string.")
        if max_age_days is not None and max_age_days < 0:
            raise ValueError("max_age_days retention cannot be negative.")

        logger.info(
            "[CheckpointManager] Starting safe purge: project=%s migration=%s (retention=%s days)",
            project_id, migration_id, max_age_days if max_age_days is not None else "None"
        )
        
        # Load all checkpoints for this migration
        records = await self.storage.list_by_migration(project_id, migration_id)
        deleted_count = 0
        now = datetime.now(timezone.utc)

        for record in records:
            # 1. Status constraint: NEVER purge PENDING or COMMITTED checkpoints
            if record.status not in (CheckpointStatus.FAILED, CheckpointStatus.COMPLETED):
                logger.debug(
                    "[CheckpointManager] Skipping purge for checkpoint %s (status: %s is protected)",
                    record.checkpoint_id, record.status.value
                )
                continue

            # 2. Age constraint: if max_age_days is specified, only purge if older than now - delta
            if max_age_days is not None:
                record_time = None
                try:
                    # Created_at parsing
                    record_time = datetime.fromisoformat(record.created_at)
                except Exception:
                    try:
                        record_time = datetime.fromisoformat(record.updated_at)
                    except Exception:
                        pass

                if record_time:
                    # Make offset-aware if timezone is naive
                    if record_time.tzinfo is None:
                        record_time = record_time.replace(tzinfo=timezone.utc)
                    
                    age = now - record_time
                    if age.days < max_age_days:
                        # Inside retention window; do not purge
                        logger.debug(
                            "[CheckpointManager] Skipping purge for checkpoint %s (age: %d days < retention limit)",
                            record.checkpoint_id, age.days
                        )
                        continue

            # If it passes safety criteria, delete it
            success = await self.storage.delete(record.checkpoint_id)
            if success:
                deleted_count += 1
                try:
                    if self._metrics is not None:
                        self._metrics.counter("checkpoint_purge_count").increment()
                except Exception:
                    pass
                logger.debug("[CheckpointManager] Safely purged checkpoint %s", record.checkpoint_id)

        logger.info("[CheckpointManager] Safe purge completed. Deleted %d checkpoints.", deleted_count)
        return deleted_count
