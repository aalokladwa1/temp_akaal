"""
Akaal — Checkpoint & Recovery Subsystem
========================================
Implements production-grade checkpointing, persistence, and failure recovery.
"""

from akaal.core.checkpoint.checkpoint_record import CheckpointRecord, CheckpointStatus
from akaal.core.checkpoint.checkpoint_manager import CheckpointManager
from akaal.core.checkpoint.storage.base_storage import ICheckpointStorageAdapter
from akaal.core.checkpoint.storage.file_storage import FileCheckpointStorageAdapter
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
from akaal.core.checkpoint.storage.factory import CheckpointStorageFactory

__all__ = [
    "CheckpointRecord",
    "CheckpointStatus",
    "CheckpointManager",
    "ICheckpointStorageAdapter",
    "FileCheckpointStorageAdapter",
    "SQLiteCheckpointStorageAdapter",
    "CheckpointStorageFactory",
]
