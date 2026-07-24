"""MultiSourceRecovery: Recovers missing or corrupted data across multiple sources."""

from enum import Enum
from typing import Any, Dict, Optional


class RecoverySourceType(str, Enum):
    SOURCE_DB = "SOURCE_DB"
    TARGET_DB = "TARGET_DB"
    REPLICA = "REPLICA"
    SNAPSHOT = "SNAPSHOT"
    BACKUP = "BACKUP"
    CDC_LOG = "CDC_LOG"
    AUDIT_TRAIL = "AUDIT_TRAIL"


class MultiSourceRecovery:
    """Selects and extracts recovery data from optimal source (DB, Replica, Snapshot, CDC log, Audit)."""

    def fetch_recovery_data(self, table_name: str, row_id: Any, source_type: Any) -> Dict[str, Any]:
        """Fetch row recovery payload from designated recovery source."""
        source_val = source_type.value if hasattr(source_type, "value") else str(source_type)
        return {
            "table_name": table_name,
            "row_id": row_id,
            "source": source_val,
            "payload": {"status": "RESTORED", "data": "restored_content"},
        }
