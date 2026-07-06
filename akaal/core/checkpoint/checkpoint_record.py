"""
Akaal — Checkpoint Record Model
================================
Defines the schema and representation of a production checkpoint record.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from akaal.core.models.enums import WorkflowState

logger = logging.getLogger("akaal.core.checkpoint.record")


class CheckpointStatus(str, Enum):
    """Enumeration of possible checkpoint statuses."""
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CORRUPT = "CORRUPT"


@dataclass
class CheckpointRecord:
    """
    Upgraded production checkpoint record representing the exact progress state 
    of a data migration batch execution.
    """
    checkpoint_id: str
    project_id: str
    migration_id: str
    workflow_state: WorkflowState
    table_name: str
    batch_number: int
    worker_id: Optional[str] = "default"
    last_processed_primary_key: Optional[Dict[str, Any]] = None  # Key-value mapping of cursors
    rows_processed: int = 0
    rows_failed: int = 0
    rows_skipped: int = 0
    retry_count: int = 0
    adapter_state: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: CheckpointStatus = CheckpointStatus.PENDING

    def calculate_checksum(self) -> str:
        """
        Calculate SHA-256 checksum of the record based on immutable migration progress fields.
        Excludes mutable fields: checksum, status, updated_at, metrics.
        """
        payload = {
            "checkpoint_id": self.checkpoint_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "workflow_state": self.workflow_state.value,
            "table_name": self.table_name,
            "batch_number": self.batch_number,
            "worker_id": self.worker_id,
            "last_processed_primary_key": self.last_processed_primary_key,
            "rows_processed": self.rows_processed,
            "rows_failed": self.rows_failed,
            "rows_skipped": self.rows_skipped,
            "retry_count": self.retry_count,
            "adapter_state": self.adapter_state,
            "created_at": self.created_at,
        }
        # Sort keys to ensure stable serialization order
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload_bytes).hexdigest()

    def verify_integrity(self) -> bool:
        """
        Verify the integrity of this record by recalculating the checksum and
        comparing it against the stored checksum attribute.
        """
        if not self.checksum:
            logger.warning("[CheckpointRecord:%s] Checksum is missing.", self.checkpoint_id)
            return False
        computed = self.calculate_checksum()
        is_valid = computed == self.checksum
        if not is_valid:
            logger.error(
                "[CheckpointRecord:%s] Checksum mismatch. Stored: %s, Computed: %s",
                self.checkpoint_id, self.checksum, computed
            )
        return is_valid

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the checkpoint record to a dictionary representation."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "workflow_state": self.workflow_state.value,
            "table_name": self.table_name,
            "batch_number": self.batch_number,
            "worker_id": self.worker_id,
            "last_processed_primary_key": self.last_processed_primary_key,
            "rows_processed": self.rows_processed,
            "rows_failed": self.rows_failed,
            "rows_skipped": self.rows_skipped,
            "retry_count": self.retry_count,
            "adapter_state": self.adapter_state,
            "metrics": self.metrics,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointRecord":
        """Deserialize a dictionary representation back to a CheckpointRecord instance."""
        status_str = data.get("status")
        try:
            status_enum = CheckpointStatus(status_str) if status_str else CheckpointStatus.PENDING
        except ValueError:
            # Fallback for legacy status strings
            status_enum = CheckpointStatus.COMMITTED if data.get("checksum") else CheckpointStatus.PENDING

        # Ensure last_processed_primary_key is parsed as a dictionary if it is stored as a JSON string
        pk_cursor = data.get("last_processed_primary_key")
        if isinstance(pk_cursor, str):
            try:
                pk_cursor = json.loads(pk_cursor)
            except json.JSONDecodeError:
                pk_cursor = {"legacy_offset": pk_cursor}

        return cls(
            checkpoint_id=data["checkpoint_id"],
            project_id=data["project_id"],
            migration_id=data["migration_id"],
            workflow_state=WorkflowState(data["workflow_state"]),
            table_name=data["table_name"],
            batch_number=data["batch_number"],
            worker_id=data.get("worker_id", "default"),
            last_processed_primary_key=pk_cursor,
            rows_processed=data.get("rows_processed", 0),
            rows_failed=data.get("rows_failed", 0),
            rows_skipped=data.get("rows_skipped", 0),
            retry_count=data.get("retry_count", 0),
            adapter_state=data.get("adapter_state", {}),
            metrics=data.get("metrics", {}),
            checksum=data.get("checksum", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            status=status_enum,
        )
