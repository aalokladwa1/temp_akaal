"""
Akaal — Execution Timeline Model
================================
Defines execution flow, entry/exit criteria, estimated durations, parallel regions, and boundaries.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TimelineStageEntry:
    stage_id: str
    stage_name: str
    estimated_duration_minutes: float
    entry_criteria: List[str] = field(default_factory=list)
    exit_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    parallel_region_id: Optional[str] = None
    has_checkpoint_boundary: bool = False
    has_rollback_window: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "entry_criteria": self.entry_criteria,
            "exit_criteria": self.exit_criteria,
            "dependencies": self.dependencies,
            "parallel_region_id": self.parallel_region_id,
            "has_checkpoint_boundary": self.has_checkpoint_boundary,
            "has_rollback_window": self.has_rollback_window,
        }


@dataclass
class ExecutionTimeline:
    total_estimated_duration_minutes: float = 0.0
    timeline_stages: List[TimelineStageEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_estimated_duration_minutes": round(self.total_estimated_duration_minutes, 2),
            "timeline_stages": [s.to_dict() for s in self.timeline_stages],
        }
