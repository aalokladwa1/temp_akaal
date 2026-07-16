import threading
from typing import Dict, List, Optional
from akaal.migration.versioning.models import ObjectVersionSnapshot

class VersionRegistry:
    """Thread-safe registry to store and manage versioned snapshots of migration objects."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshots: Dict[str, ObjectVersionSnapshot] = {}
        self._frozen: bool = False

    def register(self, snapshot: ObjectVersionSnapshot) -> None:
        """Registers a snapshot, checking for duplicate IDs and frozen state."""
        if self._frozen:
            raise ValueError("Registry is frozen and cannot accept modifications.")
            
        with self._lock:
            version_id = snapshot.metadata.version_id
            if version_id in self._snapshots:
                raise ValueError(f"Version ID '{version_id}' is already registered.")
            self._snapshots[version_id] = snapshot

    def get(self, version_id: str) -> Optional[ObjectVersionSnapshot]:
        with self._lock:
            return self._snapshots.get(version_id)

    def list_all(self) -> List[ObjectVersionSnapshot]:
        with self._lock:
            return list(self._snapshots.values())

    def freeze(self) -> None:
        with self._lock:
            self._frozen = True

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._frozen = False
