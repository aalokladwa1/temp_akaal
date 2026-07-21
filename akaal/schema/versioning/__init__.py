"""
AKAAL Platform 5 — Metadata Version Control Subsystem
"""

from akaal.schema.versioning.snapshot import SchemaSnapshot
from akaal.schema.versioning.graph import VersionDAG, VersionNode
from akaal.schema.versioning.merge import VersionMergeEngine, MergeResult, MergeConflict
from akaal.schema.versioning.repository import VersionRepository
from akaal.schema.versioning.manager import MetadataVersionManager, VersionDiff

__all__ = [
    "SchemaSnapshot",
    "VersionDAG",
    "VersionNode",
    "VersionMergeEngine",
    "MergeResult",
    "MergeConflict",
    "VersionRepository",
    "MetadataVersionManager",
    "VersionDiff",
]
