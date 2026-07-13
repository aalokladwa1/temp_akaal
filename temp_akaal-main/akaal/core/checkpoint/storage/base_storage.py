"""
Akaal — Checkpoint Storage Interface
=====================================
Defines the interface for all checkpoint persistence storage adapters.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from akaal.core.checkpoint.checkpoint_record import CheckpointRecord


class ICheckpointStorageAdapter(ABC):
    """
    Abstract Base Class defining the required storage operations for checkpoints.
    All storage engines (SQLite, PostgreSQL, JSON Files, etc.) must implement this interface.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Perform any necessary schema creation, validation, or filesystem setup.
        Must be safe to run multiple times (idempotent).
        """
        pass

    @abstractmethod
    async def write(self, record: CheckpointRecord) -> bool:
        """
        Write or update a CheckpointRecord.
        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        pass

    @abstractmethod
    async def read(self, checkpoint_id: str) -> Optional[CheckpointRecord]:
        """
        Retrieve a CheckpointRecord by its unique identifier.
        Returns:
            Optional[CheckpointRecord]: The record if found, or None.
        """
        pass

    @abstractmethod
    async def read_latest(
        self, project_id: str, migration_id: str, table_name: Optional[str] = None
    ) -> Optional[CheckpointRecord]:
        """
        Retrieve the most recently updated valid CheckpointRecord matching the filters.
        Used primarily during crash recovery to identify the resume position.
        Returns:
            Optional[CheckpointRecord]: The latest record, or None.
        """
        pass

    @abstractmethod
    async def list_by_migration(
        self, project_id: str, migration_id: str
    ) -> List[CheckpointRecord]:
        """
        List all CheckpointRecords logged for a given migration session.
        Returns:
            List[CheckpointRecord]: Chronologically sorted list of records.
        """
        pass

    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        """
        Delete a CheckpointRecord.
        Returns:
            bool: True if deleted successfully, False if not found or failed.
        """
        pass

    @abstractmethod
    async def clear_migration(self, project_id: str, migration_id: str) -> int:
        """
        Purge all checkpoints related to a specific migration.
        Returns:
            int: The number of deleted records.
        """
        pass
