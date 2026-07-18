"""
Akaal — Cutover Plan & Cutover Phase Model
==========================================
Deterministic cutover strategy with immutable phases.
Planner plans cutover but never executes it.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CutoverPhaseType(str, Enum):
    PREPARATION = "PREPARATION"
    FREEZE = "FREEZE"
    SYNCHRONIZATION = "SYNCHRONIZATION"
    VALIDATION = "VALIDATION"
    SWITCH = "SWITCH"
    MONITORING = "MONITORING"
    ROLLBACK_WINDOW = "ROLLBACK_WINDOW"
    COMPLETION = "COMPLETION"


@dataclass
class CutoverPhase:
    phase_id: str
    phase_type: CutoverPhaseType
    estimated_duration_minutes: float = 5.0
    entry_criteria: List[str] = field(default_factory=list)
    exit_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "phase_type": self.phase_type.value if hasattr(self.phase_type, "value") else str(self.phase_type),
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "entry_criteria": self.entry_criteria,
            "exit_criteria": self.exit_criteria,
            "dependencies": self.dependencies,
        }


@dataclass
class CutoverPlan:
    strategy: str = "BULK_CUTOVER"
    phases: List[CutoverPhase] = field(default_factory=list)
    rollback_window_minutes: float = 30.0
    total_estimated_duration_minutes: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "phases": [p.to_dict() for p in self.phases],
            "rollback_window_minutes": self.rollback_window_minutes,
            "total_estimated_duration_minutes": round(self.total_estimated_duration_minutes, 2),
        }
