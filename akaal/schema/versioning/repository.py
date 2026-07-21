"""
AKAAL Platform 5 — Version Repository

Provides thread-safe persistence and retrieval of SchemaSnapshots and version metadata.
"""

from dataclasses import dataclass
import threading
from typing import Dict, List, Optional

from akaal.schema.domain.errors import MetadataError
from akaal.schema.domain.identifiers import SnapshotID, VersionID
from akaal.schema.versioning.snapshot import SchemaSnapshot


class VersionRepository:
    """Thread-safe in-memory/durable version repository."""

    def __init__(self) -> None:
        self._mutex = threading.RLock()
        self._snapshots_by_ver: Dict[str, SchemaSnapshot] = {}
        self._snapshots_by_id: Dict[str, SchemaSnapshot] = {}
        self._version_order: List[VersionID] = []

    def save_snapshot(self, snapshot: SchemaSnapshot) -> None:
        with self._mutex:
            if not snapshot.verify_integrity():
                raise MetadataError(
                    message=f"Snapshot checksum mismatch for version '{snapshot.version_id}'. Data corrupted.",
                    recovery_recommendation="Re-generate snapshot from underlying schema metadata."
                )
            ver_str = str(snapshot.version_id)
            snap_str = str(snapshot.snapshot_id)
            self._snapshots_by_ver[ver_str] = snapshot
            self._snapshots_by_id[snap_str] = snapshot
            if snapshot.version_id not in self._version_order:
                self._version_order.append(snapshot.version_id)

    def get_by_version(self, version_id: VersionID) -> Optional[SchemaSnapshot]:
        with self._mutex:
            return self._snapshots_by_ver.get(str(version_id))

    def get_latest(self) -> Optional[SchemaSnapshot]:
        with self._mutex:
            if not self._version_order:
                return None
            return self._snapshots_by_ver.get(str(self._version_order[-1]))

    def list_versions(self) -> List[VersionID]:
        with self._mutex:
            return list(self._version_order)
