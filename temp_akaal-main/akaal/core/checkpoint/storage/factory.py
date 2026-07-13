"""
Akaal — Checkpoint Storage Adapter Factory
===========================================
Instantiates storage adapters dynamically based on configuration.
"""

import os
from typing import Any, Optional

from akaal.core.checkpoint.storage.base_storage import ICheckpointStorageAdapter
from akaal.core.checkpoint.storage.file_storage import FileCheckpointStorageAdapter
from akaal.core.checkpoint.storage.sqlite_storage import SQLiteCheckpointStorageAdapter


class CheckpointStorageFactory:
    """
    Factory to construct the appropriate implementation of ICheckpointStorageAdapter.
    Prevents high-level pipeline and agent layers from needing direct dependencies on
    concrete storage classes.
    """

    @staticmethod
    def create(
        config: Any = None, storage_type: Optional[str] = None, **kwargs: Any
    ) -> ICheckpointStorageAdapter:
        """
        Instantiate and return the requested checkpoint storage adapter.
        Args:
            config: A dictionary of configuration options, or an object (e.g. MigrationConfig)
                    possessing a `workspace_dir` attribute.
            storage_type: Explicit override of the storage engine type ('sqlite', 'file').
            **kwargs: Extra parameters passed directly to the adapter constructors.
        Returns:
            ICheckpointStorageAdapter: An initialized storage adapter instance.
        """
        resolved_type = "file"
        resolved_config = {}

        if isinstance(config, dict):
            resolved_config.update(config)
            resolved_type = config.get("type") or config.get("storage_type") or "file"
        elif config is not None:
            # Assume it's a configuration object (e.g., MigrationConfig)
            workspace = getattr(config, "workspace_dir", "./akaal_workspace")
            resolved_config["workspace_dir"] = workspace
            resolved_config["db_path"] = os.path.join(workspace, "checkpoints.db")
            resolved_type = getattr(config, "checkpoint_storage_type", "file")

        # Overlay parameters passed via kwargs
        if storage_type:
            resolved_type = storage_type
        resolved_config.update(kwargs)

        resolved_type = resolved_type.strip().lower()

        if resolved_type in ("sqlite", "sqlite3", "db", "database"):
            db_path = resolved_config.get("db_path")
            if not db_path:
                workspace = resolved_config.get("workspace_dir", "./akaal_workspace")
                db_path = os.path.join(workspace, "checkpoints.db")
            return SQLiteCheckpointStorageAdapter(db_path)

        elif resolved_type in ("file", "json", "filesystem"):
            workspace = resolved_config.get("workspace_dir", "./akaal_workspace")
            return FileCheckpointStorageAdapter(workspace)

        else:
            raise ValueError(
                f"Unsupported checkpoint storage type: '{resolved_type}'. "
                "Supported options are: 'sqlite', 'file'."
            )
