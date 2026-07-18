"""
Akaal — Checkpoint Plan Model
=============================
CheckpointPlan model defining checkpoint strategy, locations, frequency, and recovery boundaries.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CheckpointLocation:
    checkpoint_id: str
    task_id: str
    stage_id: str
    checkpoint_type: str = "STAGE_BOUNDARY"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "stage_id": self.stage_id,
            "checkpoint_type": self.checkpoint_type,
        }


@dataclass
class CheckpointPlan:
    strategy: str = "STAGE_BOUNDARY"
    frequency: str = "AFTER_EACH_STAGE"
    locations: List[CheckpointLocation] = field(default_factory=list)
    resume_points: List[str] = field(default_factory=list)
    validation_gates: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "frequency": self.frequency,
            "locations": [loc.to_dict() for loc in self.locations],
            "resume_points": self.resume_points,
            "validation_gates": self.validation_gates,
        }
