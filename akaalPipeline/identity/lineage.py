"""akaalPipeline.identity.lineage
===============================
Tracks migration definition, clone, and rerun lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LineageType(str, Enum):
    ROOT = "ROOT"
    CLONE = "CLONE"
    RERUN = "RERUN"
    REVISION_UPGRADE = "REVISION_UPGRADE"


@dataclass(frozen=True)
class LineageRecord:
    lineage_type: LineageType
    parent_migration_id: Optional[str] = None
    parent_revision_id: Optional[str] = None
    parent_initialization_id: Optional[str] = None
    reason: Optional[str] = None

    @classmethod
    def root(cls) -> LineageRecord:
        return cls(lineage_type=LineageType.ROOT)

    def to_dict(self) -> dict:

        return {
            "lineage_type": self.lineage_type.value,
            "parent_migration_id": self.parent_migration_id,
            "parent_revision_id": self.parent_revision_id,
            "parent_initialization_id": self.parent_initialization_id,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LineageRecord:
        return cls(
            lineage_type=LineageType(data["lineage_type"]),
            parent_migration_id=data.get("parent_migration_id"),
            parent_revision_id=data.get("parent_revision_id"),
            parent_initialization_id=data.get("parent_initialization_id"),
            reason=data.get("reason"),
        )


class LineageTracker:
    @staticmethod
    def root() -> LineageRecord:
        return LineageRecord(lineage_type=LineageType.ROOT)

    @staticmethod
    def clone(parent_migration_id: str, parent_revision_id: str, reason: str = "Cloned migration definition") -> LineageRecord:
        return LineageRecord(
            lineage_type=LineageType.CLONE,
            parent_migration_id=parent_migration_id,
            parent_revision_id=parent_revision_id,
            reason=reason,
        )

    @staticmethod
    def rerun(parent_migration_id: str, parent_initialization_id: str, reason: str = "Rerun from initialization") -> LineageRecord:
        return LineageRecord(
            lineage_type=LineageType.RERUN,
            parent_migration_id=parent_migration_id,
            parent_initialization_id=parent_initialization_id,
            reason=reason,
        )
