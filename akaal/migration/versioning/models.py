import uuid
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any
from akaal.migration.models import ObjectType

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
class ObjectVersionSnapshot:
    """A frozen version snapshot containing full serialized object representation."""
    metadata: VersionMetadata
    serialized_payload: str

@dataclass(frozen=True)
class VersionDiff:
    """Summary of changes between two snapshots of an object."""
    from_version_id: Optional[str]
    to_version_id: str
    object_key: str
    change_type: str
    diff_details: Dict[str, Any] = field(default_factory=dict)
