"""
Akaal — File Checkpoint Storage Adapter
========================================
Persists checkpoints to local JSON files under the projects directory.
"""

import asyncio
import glob
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.checkpoint.checkpoint_record import CheckpointRecord
from akaal.core.checkpoint.storage.base_storage import ICheckpointStorageAdapter
from akaal.core.models.enums import WorkflowState

logger = logging.getLogger("akaal.core.checkpoint.storage.file")


class FileCheckpointStorageAdapter(ICheckpointStorageAdapter):
    """
    Saves and reads checkpoint JSON files to/from the local filesystem.
    Maintains backward compatibility with older-format checkpoints.
    """

    def __init__(self, workspace_dir: str) -> None:
        """
        Initialize the file storage adapter.
        Args:
            workspace_dir: Path to the workspace base directory.
        """
        self.workspace_dir = workspace_dir
        logger.debug("[FileStorage] Initialized with workspace: %s", workspace_dir)

    async def initialize(self) -> None:
        """Create workspace directory if it doesn't exist."""
        def _init():
            os.makedirs(self.workspace_dir, exist_ok=True)
        await asyncio.to_thread(_init)

    def _get_project_dir(self, project_id: str) -> str:
        return os.path.join(self.workspace_dir, "projects", project_id)

    def _get_file_path(self, project_id: str, checkpoint_id: str) -> str:
        return os.path.join(self._get_project_dir(project_id), f"checkpoint_{checkpoint_id}.json")

    async def write(self, record: CheckpointRecord) -> bool:
        """Write record to a local JSON file."""
        if not record:
            logger.warning("[FileStorage] Attempted to write empty record.")
            return False

        def _write():
            try:
                record.updated_at = datetime.now(timezone.utc).isoformat()
                record.checksum = record.calculate_checksum()
                from akaal.core.checkpoint.checkpoint_record import CheckpointStatus
                if record.status == CheckpointStatus.PENDING:
                    record.status = CheckpointStatus.COMMITTED
                
                project_dir = self._get_project_dir(record.project_id)
                os.makedirs(project_dir, exist_ok=True)
                
                file_path = self._get_file_path(record.project_id, record.checkpoint_id)
                
                # To maintain compatibility with older format, we dump the record dict.
                # Older format had a 'payload' and 'description' field. We can serialize
                # those if present, or just serialization of record fields.
                data = record.to_dict()
                
                # Keep compatibility structure (legacy checkpoints had "payload")
                data["payload"] = {
                    "project_state": {
                        "state": record.workflow_state.value,
                    },
                    "global_state_snapshot": record.adapter_state.get("global_state_snapshot", {})
                }
                data["description"] = record.metrics.get("description", "Workflow checkpoint")
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                
                logger.info("[FileStorage] Checkpoint %s saved to %s", record.checkpoint_id, file_path)
                return True
            except Exception as e:
                logger.error("[FileStorage] Failed to write checkpoint %s: %s", record.checkpoint_id, e, exc_info=True)
                return False

        return await asyncio.to_thread(_write)

    async def read(self, checkpoint_id: str) -> Optional[CheckpointRecord]:
        """Read checkpoint from local JSON file. Scans files under the workspace project dirs."""
        # Find file path dynamically since project_id is not passed to read()
        def _read():
            pattern = os.path.join(self.workspace_dir, "projects", "*", f"checkpoint_{checkpoint_id}.json")
            files = glob.glob(pattern)
            if not files:
                logger.warning("[FileStorage] Checkpoint %s file not found.", checkpoint_id)
                return None
            
            file_path = files[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._parse_compatible_record(data)
            except Exception as e:
                logger.error("[FileStorage] Failed to read checkpoint %s: %s", checkpoint_id, e, exc_info=True)
                return None

        return await asyncio.to_thread(_read)

    async def read_latest(
        self, project_id: str, migration_id: str, table_name: Optional[str] = None
    ) -> Optional[CheckpointRecord]:
        """Scan project files for the latest matching checkpoint record."""
        def _read_latest():
            project_dir = self._get_project_dir(project_id)
            if not os.path.exists(project_dir):
                return None

            pattern = os.path.join(project_dir, "checkpoint_*.json")
            files = glob.glob(pattern)
            
            matching_records: List[CheckpointRecord] = []
            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Parse the record with compatibility mappings
                    record = self._parse_compatible_record(data)
                    if not record:
                        continue
                    
                    # Filter check
                    if record.migration_id != migration_id:
                        continue
                    if table_name and record.table_name != table_name:
                        continue
                    
                    matching_records.append(record)
                except Exception as e:
                    logger.debug("[FileStorage] Error reading file %s during latest search: %s", file_path, e)
                    continue
            
            if not matching_records:
                return None
            
            # Find the most recently updated checkpoint
            # Using updated_at or created_at
            return max(matching_records, key=lambda r: r.updated_at or r.created_at)

        return await asyncio.to_thread(_read_latest)

    async def list_by_migration(
        self, project_id: str, migration_id: str
    ) -> List[CheckpointRecord]:
        """List checkpoints by migration, sorted chronologically."""
        def _list():
            project_dir = self._get_project_dir(project_id)
            if not os.path.exists(project_dir):
                return []

            pattern = os.path.join(project_dir, "checkpoint_*.json")
            files = glob.glob(pattern)
            
            records: List[CheckpointRecord] = []
            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    record = self._parse_compatible_record(data)
                    if record and record.migration_id == migration_id:
                        records.append(record)
                except Exception as e:
                    logger.warning("[FileStorage] Error reading file %s: %s", file_path, e)
            
            # Sort chronologically by created_at
            records.sort(key=lambda r: r.created_at)
            return records

        return await asyncio.to_thread(_list)

    async def delete(self, checkpoint_id: str) -> bool:
        """Delete checkpoint file."""
        def _delete():
            pattern = os.path.join(self.workspace_dir, "projects", "*", f"checkpoint_{checkpoint_id}.json")
            files = glob.glob(pattern)
            if not files:
                return False
            try:
                os.remove(files[0])
                logger.info("[FileStorage] Deleted checkpoint file %s", files[0])
                return True
            except Exception as e:
                logger.error("[FileStorage] Error deleting checkpoint file %s: %s", files[0], e)
                return False

        return await asyncio.to_thread(_delete)

    async def clear_migration(self, project_id: str, migration_id: str) -> int:
        """Clear all checkpoints belonging to migration_id."""
        def _clear():
            project_dir = self._get_project_dir(project_id)
            if not os.path.exists(project_dir):
                return 0

            pattern = os.path.join(project_dir, "checkpoint_*.json")
            files = glob.glob(pattern)
            deleted_count = 0
            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    record = self._parse_compatible_record(data)
                    if record and record.migration_id == migration_id:
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    logger.warning("[FileStorage] Error during clear on %s: %s", file_path, e)
            logger.info("[FileStorage] Cleared %d checkpoint files for migration %s", deleted_count, migration_id)
            return deleted_count

        return await asyncio.to_thread(_clear)

    def _parse_compatible_record(self, data: Dict[str, Any]) -> Optional[CheckpointRecord]:
        """Parse dictionary, providing defaults and mapping backward-compatible legacy structures."""
        try:
            # Handle legacy/backward-compatible field names
            # Map legacy 'workflow_state' if stored in payload/project_state/state
            state_val = data.get("workflow_state")
            if not state_val and "payload" in data:
                state_val = data["payload"].get("project_state", {}).get("state")
            
            if not state_val:
                state_val = "IDLE"

            # Reconstruct record
            record = CheckpointRecord(
                checkpoint_id=data["checkpoint_id"],
                project_id=data["project_id"],
                migration_id=data["migration_id"],
                workflow_state=WorkflowState(state_val),
                table_name=data.get("table_name", ""),
                batch_number=data.get("batch_number", 0),
                worker_id=data.get("worker_id", "legacy"),
                last_processed_primary_key=data.get("last_processed_primary_key"),
                rows_processed=data.get("rows_processed", 0),
                rows_failed=data.get("rows_failed", 0),
                rows_skipped=data.get("rows_skipped", 0),
                retry_count=data.get("retry_count", 0),
                adapter_state=data.get("adapter_state", {}),
                metrics=data.get("metrics", {}),
                checksum=data.get("checksum", ""),
                created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
                updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                status=data.get("status", "COMMITTED" if data.get("checksum") else "PENDING"),
            )
            
            # Map snapshot to adapter_state if legacy (meaning adapter_state was not present at root)
            if "adapter_state" not in data and "payload" in data and "global_state_snapshot" in data["payload"]:
                record.adapter_state["global_state_snapshot"] = data["payload"]["global_state_snapshot"]
                
            return record
        except Exception as e:
            logger.error("[FileStorage] Compatibility parsing failed: %s", e)
            return None
