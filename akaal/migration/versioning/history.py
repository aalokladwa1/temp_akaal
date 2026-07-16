import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple
from akaal.migration.models import MigrationObject
from akaal.migration.hashing import canonicalize_migration_object, canonicalize_metadata
from akaal.migration.versioning.models import VersionMetadata, ObjectVersionSnapshot

class ConcurrencyConflictError(Exception):
    """Exception raised when optimistic lock tokens do not match the target parent version."""
    pass

class ObjectVersionHistory:
    """Manages immutable snapshots and audits changes with optimistic locking."""
    def __init__(self) -> None:
        self._history: Dict[str, List[ObjectVersionSnapshot]] = {}

    def commit_version(
        self,
        obj: MigrationObject,
        created_by: str,
        expected_parent_id: Optional[str] = None,
        tags: Tuple[str, ...] = ()
    ) -> ObjectVersionSnapshot:
        """
        Creates and commits a new version snapshot.
        Enforces optimistic locking validation against expected_parent_id.
        """
        object_key = obj.object_key
        history_list = self._history.setdefault(object_key, [])

        # Concurrency verification
        current_leaf: Optional[ObjectVersionSnapshot] = history_list[-1] if history_list else None
        if current_leaf:
            if expected_parent_id is not None and current_leaf.metadata.version_id != expected_parent_id:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict: expected parent version '{expected_parent_id}' "
                    f"but active version is '{current_leaf.metadata.version_id}'"
                )
        elif expected_parent_id is not None:
            raise ConcurrencyConflictError("Expected parent version specified but no history exists.")

        # Hashing Calculations
        fingerprint = self._calculate_fingerprint(obj)
        schema_hash = self._calculate_schema_hash(obj)
        ddl_hash = self._calculate_ddl_hash(obj)
        metadata_hash = self._calculate_metadata_hash(obj)

        change_type = "UPDATE"
        if not current_leaf:
            change_type = "CREATE"
        elif current_leaf.metadata.fingerprint == fingerprint:
            change_type = "NONE"

        # Construct snapshot payload
        serialized = json.dumps(canonicalize_migration_object(obj), sort_keys=True)
        version_id = str(uuid.uuid4())
        
        meta = VersionMetadata(
            version_id=version_id,
            parent_version_id=current_leaf.metadata.version_id if current_leaf else None,
            object_type=obj.object_type,
            object_name=obj.name,
            fingerprint=fingerprint,
            schema_hash=schema_hash,
            ddl_hash=ddl_hash,
            metadata_hash=metadata_hash,
            generated_at=time.time(),
            created_by=created_by,
            optimistic_lock_token=fingerprint[:16],  # Lock token derived from fingerprint
            change_type=change_type,
            tags=tags
        )

        snapshot = ObjectVersionSnapshot(metadata=meta, serialized_payload=serialized)
        history_list.append(snapshot)
        return snapshot

    def get_history(self, object_key: str) -> List[ObjectVersionSnapshot]:
        return list(self._history.get(object_key, []))

    def _calculate_fingerprint(self, obj: MigrationObject) -> str:
        payload = json.dumps(canonicalize_migration_object(obj), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _calculate_schema_hash(self, obj: MigrationObject) -> str:
        # Schema definition variables
        schema_dict = {
            "name": obj.name,
            "type": obj.object_type.value if hasattr(obj.object_type, "value") else str(obj.object_type),
            "schema": obj.schema
        }
        if hasattr(obj, "data_type"):
            schema_dict["data_type"] = obj.data_type
            schema_dict["nullable"] = obj.nullable
        if hasattr(obj, "constraint_type"):
            schema_dict["constraint_type"] = obj.constraint_type
            schema_dict["columns"] = tuple(obj.columns)
        
        payload = json.dumps(schema_dict, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _calculate_ddl_hash(self, obj: MigrationObject) -> str:
        # Standard structural representation hash
        ddl_repr = f"CREATE {obj.object_type.value} {obj.object_key}"
        return hashlib.sha256(ddl_repr.encode("utf-8")).hexdigest()

    def _calculate_metadata_hash(self, obj: MigrationObject) -> str:
        meta_dict = {
            "attributes": canonicalize_metadata(obj.attributes),
            "vendor_metadata": canonicalize_metadata(obj.vendor_metadata)
        }
        payload = json.dumps(meta_dict, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
