"""
AKAAL Platform 5 — MetadataVersionManager

High-level manager for creating snapshots, version graph tracking, version diffing, and rollback metadata.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional

from akaal.schema.domain.identifiers import SnapshotID, VersionID
from akaal.schema.observability.logger import StructuredAuditLogger
from akaal.schema.versioning.graph import VersionDAG, VersionNode
from akaal.schema.versioning.repository import VersionRepository
from akaal.schema.versioning.snapshot import SchemaSnapshot


@dataclass
class VersionDiff:
    from_version: VersionID
    to_version: VersionID
    added_tables: List[str]
    removed_tables: List[str]
    modified_tables: Dict[str, Dict[str, Any]]


class MetadataVersionManager:
    """Manager for schema version control, snapshots, diffing, and rollback metadata."""

    def __init__(self, repository: Optional[VersionRepository] = None, dag: Optional[VersionDAG] = None) -> None:
        self.repository = repository or VersionRepository()
        self.dag = dag or VersionDAG()
        self.audit_logger = StructuredAuditLogger("akaal.schema.versioning")

    def create_snapshot(
        self,
        tables: Dict[str, Any],
        views: Optional[Dict[str, Any]] = None,
        sequences: Optional[Dict[str, Any]] = None,
        parent_version_ids: Optional[List[VersionID]] = None,
        author: str = "system",
        commit_message: str = "",
    ) -> SchemaSnapshot:
        ver_id = VersionID.generate()
        snap_id = SnapshotID.generate()
        parents = parent_version_ids or []

        snapshot = SchemaSnapshot(
            snapshot_id=snap_id,
            version_id=ver_id,
            tables=tables,
            views=views or {},
            sequences=sequences or {},
            metadata={"author": author, "commit_message": commit_message},
        )
        self.repository.save_snapshot(snapshot)

        node = VersionNode(
            version_id=ver_id,
            parent_ids=parents,
            author=author,
            commit_message=commit_message,
            timestamp=time.time(),
        )
        self.dag.add_version(node)

        self.audit_logger.log_event(
            "SNAPSHOT_CREATED",
            details={
                "version_id": str(ver_id),
                "snapshot_id": str(snap_id),
                "table_count": len(tables),
                "author": author,
            },
        )
        return snapshot

    def diff_versions(self, from_version: VersionID, to_version: VersionID) -> VersionDiff:
        snap_from = self.repository.get_by_version(from_version)
        snap_to = self.repository.get_by_version(to_version)

        tables_from = snap_from.tables if snap_from else {}
        tables_to = snap_to.tables if snap_to else {}

        keys_from = set(tables_from.keys())
        keys_to = set(tables_to.keys())

        added = list(keys_to - keys_from)
        removed = list(keys_from - keys_to)

        modified = {}
        for common in keys_from.intersection(keys_to):
            if tables_from[common] != tables_to[common]:
                modified[common] = {
                    "from": tables_from[common],
                    "to": tables_to[common],
                }

        return VersionDiff(
            from_version=from_version,
            to_version=to_version,
            added_tables=added,
            removed_tables=removed,
            modified_tables=modified,
        )
