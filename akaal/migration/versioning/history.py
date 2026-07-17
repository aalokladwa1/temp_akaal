import uuid
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from akaal.migration.versioning.models import (
    CanonicalVersionRecord,
    ObjectVersionSnapshot,
    VersionStatus,
    RollbackMetadata,
    VersionMetadata
)
from akaal.migration.versioning.version_store import VersionStore
from akaal.migration.versioning.fingerprint import FingerprintEngine
from akaal.migration.hashing import canonicalize_migration_object, canonicalize_metadata

class ConcurrencyConflictError(Exception):
    """Raised when expected parent version id does not match actual latest version id."""
    pass

class ObjectVersionHistory:
    """
    Manages linear object lineage histories, validation state checks, and commits snapshots.
    Supports both old and new commit_version signatures.
    """
    def __init__(self, store: Optional[VersionStore] = None) -> None:
        self.store = store or VersionStore()
        self.lineages: Dict[str, List[str]] = {} # object_id -> list of version_ids

    def commit_version(self, *args, **kwargs) -> ObjectVersionSnapshot:
        if args and not isinstance(args[0], str):
            # --- OLD SIGNATURE ---
            # commit_version(self, obj, created_by, expected_parent_id=None, tags=())
            obj = args[0]
            created_by = args[1] if len(args) > 1 else kwargs.get("created_by", "admin")
            expected_parent_id = args[2] if len(args) > 2 else kwargs.get("expected_parent_id", None)
            
            tags = args[3] if len(args) > 3 else kwargs.get("tags", ())
            
            object_id = obj.object_key
            history_list = self.lineages.setdefault(object_id, [])
            latest_version_id = history_list[-1] if history_list else None
            
            if expected_parent_id is not None and latest_version_id != expected_parent_id:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict: expected parent version '{expected_parent_id}' "
                    f"but active version is '{latest_version_id}'"
                )
                
            payload = json.dumps(canonicalize_migration_object(obj), sort_keys=True)
            fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            
            change_type = "UPDATE"
            if not latest_version_id:
                change_type = "CREATE"
            else:
                parent_snap = self.store.get(latest_version_id)
                if parent_snap and parent_snap.metadata.fingerprint == fingerprint:
                    change_type = "NONE"
            
            meta = VersionMetadata(
                version_id=str(uuid.uuid4()),
                parent_version_id=latest_version_id,
                object_type=obj.object_type,
                object_name=obj.name,
                fingerprint=fingerprint,
                schema_hash=fingerprint,
                ddl_hash=fingerprint,
                metadata_hash=fingerprint,
                generated_at=time.time(),
                created_by=created_by,
                optimistic_lock_token=fingerprint[:16],
                change_type=change_type,
                tags=tags
            )
            snapshot = ObjectVersionSnapshot(metadata=meta, serialized_payload=payload)
            self.store.register(snapshot)
            history_list.append(meta.version_id)
            return snapshot
        else:
            # --- NEW SIGNATURE ---
            # commit_version(self, object_id, object_type, object_name, parent_schema, dialect, definition, session_id, author, expected_parent_id=None)
            object_id = args[0]
            object_type = args[1]
            object_name = args[2]
            parent_schema = args[3]
            dialect = args[4]
            definition = args[5]
            session_id = args[6]
            author = args[7]
            expected_parent_id = args[8] if len(args) > 8 else kwargs.get("expected_parent_id", None)
            
            history_list = self.lineages.setdefault(object_id, [])
            latest_version_id = history_list[-1] if history_list else None
            
            if expected_parent_id is not None and latest_version_id != expected_parent_id:
                raise ConcurrencyConflictError(
                    f"Concurrency conflict: expected parent version '{expected_parent_id}' "
                    f"but active version is '{latest_version_id}'"
                )
                
            fingerprint = FingerprintEngine.generate_fingerprint(definition)
            
            status = VersionStatus.CREATED
            if latest_version_id:
                parent_snap = self.store.get(latest_version_id)
                if parent_snap and parent_snap.metadata.object_definition_hash != fingerprint:
                    status = VersionStatus.MODIFIED
                else:
                    status = VersionStatus.VERIFIED

            version_id = str(uuid.uuid4())
            
            rollback = RollbackMetadata(
                previous_version_id=latest_version_id,
                previous_definition=definition if latest_version_id else None,
                previous_fingerprint=fingerprint if latest_version_id else None
            )
            
            raw_str = f"{version_id}|{object_id}|{fingerprint}|{fingerprint}"
            checksum = FingerprintEngine.generate_fingerprint(raw_str)
            
            meta = CanonicalVersionRecord(
                version_id=version_id,
                object_id=object_id,
                object_type=object_type,
                object_name=object_name,
                parent_schema=parent_schema,
                database_dialect=dialect,
                object_definition_hash=fingerprint,
                canonical_metadata_hash=fingerprint,
                creation_timestamp=datetime.now(timezone.utc),
                modification_timestamp=datetime.now(timezone.utc),
                migration_session_id=session_id,
                parent_version_id=latest_version_id,
                current_version_id=version_id,
                version_status=status,
                author=author,
                rollback_metadata=rollback,
                integrity_checksum=checksum
            )
            
            snapshot = ObjectVersionSnapshot(metadata=meta, serialized_payload=definition)
            self.store.register(snapshot)
            history_list.append(version_id)
            return snapshot

    def get_history(self, object_id: str) -> List[ObjectVersionSnapshot]:
        v_ids = self.lineages.get(object_id, [])
        return [self.store.get(vid) for vid in v_ids if self.store.get(vid)]
