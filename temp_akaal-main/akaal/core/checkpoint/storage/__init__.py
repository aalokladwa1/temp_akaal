"""
Akaal — Checkpoint Storage Adapter Package
===========================================
Exposes storage adapters and factories for checkpoint persistence.
"""

from akaal.core.checkpoint.storage.base_storage import ICheckpointStorageAdapter
from akaal.core.checkpoint.storage.file_storage import FileCheckpointStorageAdapter
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter
from akaal.core.checkpoint.storage.factory import CheckpointStorageFactory

__all__ = [
    "ICheckpointStorageAdapter",
    "FileCheckpointStorageAdapter",
    "SQLiteCheckpointStorageAdapter",
    "CheckpointStorageFactory",
]
