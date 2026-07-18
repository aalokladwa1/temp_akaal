"""
Akaal — Canonical Lineage Model
===============================
Stage 1 transformation lineage tracker across normalization pipeline stages.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class LineageNode:
    stage_name: str
    source_identifier: str
    target_identifier: str
    transformation_applied: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "source_identifier": self.source_identifier,
            "target_identifier": self.target_identifier,
            "transformation_applied": self.transformation_applied,
            "timestamp": self.timestamp,
        }


@dataclass
class CanonicalLineage:
    lineage_id: str
    history: List[LineageNode] = field(default_factory=list)

    def record_stage(self, stage_name: str, source_id: str, target_id: str, tx_description: str) -> None:
        self.history.append(LineageNode(
            stage_name=stage_name,
            source_identifier=source_id,
            target_identifier=target_id,
            transformation_applied=tx_description,
        ))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "history": [h.to_dict() for h in self.history],
        }
