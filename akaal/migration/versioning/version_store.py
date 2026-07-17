import threading
import hashlib
from typing import Dict, List, Optional, Any
from akaal.migration.versioning.models import ObjectVersionSnapshot

class VersioningCorruptionException(Exception):
    """Raised when version lineage checks, parents, or checksum validations fail."""
    pass

class VersionStore:
    """
    Thread-safe persistent registry of version snapshots.
    Enforces uniqueness, lineage parent checks, and cycle preventions.
    Supports both VersionMetadata and CanonicalVersionRecord.
    """
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.snapshots: Dict[str, ObjectVersionSnapshot] = {}
        self.current_versions: Dict[str, str] = {}
        self.frozen = False

    def register(self, snapshot: ObjectVersionSnapshot) -> None:
        if self.frozen:
            raise ValueError("Version store is frozen.")
            
        with self.lock:
            meta = snapshot.metadata
            
            # 1. Uniqueness check
            if meta.version_id in self.snapshots:
                raise ValueError(f"Version ID '{meta.version_id}' is already registered.")
                
            # 2. Checksum validation
            calculated_checksum = self.calculate_checksum(snapshot)
            if hasattr(meta, "integrity_checksum") and meta.integrity_checksum:
                if meta.integrity_checksum != calculated_checksum:
                    raise VersioningCorruptionException(
                        f"Integrity checksum mismatch for version {meta.version_id}."
                    )
                
            # 3. Parent check
            if meta.parent_version_id:
                if meta.parent_version_id not in self.snapshots:
                    raise VersioningCorruptionException(
                        f"Parent version '{meta.parent_version_id}' not found for task lineage."
                    )
                # Cycle prevention check
                curr = meta.parent_version_id
                visited = {meta.version_id}
                while curr:
                    if curr in visited:
                        raise VersioningCorruptionException("Cycle detected in version lineage graph.")
                    visited.add(curr)
                    parent_snap = self.snapshots.get(curr)
                    curr = parent_snap.metadata.parent_version_id if parent_snap else None
                    
            # 4. Enforce exactly one active current version per object_id
            obj_id = getattr(meta, "object_id", getattr(meta, "object_name", ""))
            self.current_versions[obj_id] = meta.version_id
            self.snapshots[meta.version_id] = snapshot

    def get(self, version_id: str) -> Optional[ObjectVersionSnapshot]:
        with self.lock:
            return self.snapshots.get(version_id)

    def get_current(self, object_id: str) -> Optional[ObjectVersionSnapshot]:
        with self.lock:
            v_id = self.current_versions.get(object_id)
            return self.snapshots.get(v_id) if v_id else None

    def list_all(self) -> List[ObjectVersionSnapshot]:
        with self.lock:
            return list(self.snapshots.values())

    @staticmethod
    def calculate_checksum(snapshot: ObjectVersionSnapshot) -> str:
        meta = snapshot.metadata
        if hasattr(meta, "object_definition_hash"):
            raw_str = f"{meta.version_id}|{meta.object_id}|{meta.object_definition_hash}|{meta.canonical_metadata_hash}"
        else:
            raw_str = f"{meta.version_id}|{meta.object_name}|{meta.fingerprint}|{meta.fingerprint}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
