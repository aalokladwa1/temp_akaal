from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Tuple, Any, Optional
from akaal.migration.models import ObjectType

class VersionStatus(str, Enum):
    CREATED = "CREATED"
    VERIFIED = "VERIFIED"
    MIGRATED = "MIGRATED"
    MODIFIED = "MODIFIED"
    RENAMED = "RENAMED"
    DELETED = "DELETED"
    RESTORED = "RESTORED"
    ROLLED_BACK = "ROLLED_BACK"

@dataclass(frozen=True)
class RollbackMetadata:
    previous_version_id: Optional[str]
    previous_definition: Optional[str]
    previous_fingerprint: Optional[str]
    previous_dependencies: Tuple[str, ...] = ()
    previous_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class VersionMetadata:
    """Immutable version details containing audit trail metadata and rich fingerprints."""
    version_id: str
    parent_version_id: Optional[str]
    object_type: ObjectType
    object_name: str
    fingerprint: str      # Unified object state hash
    schema_hash: str      # Structural and type hash
    ddl_hash: str         # DDL CREATE syntax hash
    metadata_hash: str    # Comments and attribute hash
    generated_at: float
    created_by: str
    optimistic_lock_token: str
    change_type: str      # "CREATE", "UPDATE", "DELETE", "NONE"
    tags: Tuple[str, ...] = ()

@dataclass(frozen=True)
class CanonicalVersionRecord:
    version_id: str
    object_id: str
    object_type: str
    object_name: str
    parent_schema: str
    database_dialect: str
    object_definition_hash: str
    canonical_metadata_hash: str
    creation_timestamp: datetime
    modification_timestamp: datetime
    migration_session_id: str
    parent_version_id: Optional[str]
    current_version_id: str
    version_status: VersionStatus
    author: str
    rollback_metadata: RollbackMetadata
    integrity_checksum: str

@dataclass
class VersionMetrics:
    total_version_records: int = 0
    active_versions: int = 0
    comparisons_completed: int = 0
    fingerprint_generation_time_ms: float = 0.0
    checksum_failures: int = 0
    recovery_attempts: int = 0
    rollback_metadata_entries: int = 0
    lineage_validation_failures: int = 0

@dataclass(frozen=True)
class VersionDiff:
    from_version_id: Optional[str]
    to_version_id: str
    object_key: str
    change_type: str
    diff_details: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ObjectVersionSnapshot:
    metadata: Any  # Can be CanonicalVersionRecord or VersionMetadata
    serialized_payload: str
