"""
Akaal — Planning Trace
======================
Deterministic trace capturing step-by-step Planner pipeline decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PlanningTraceStep:
    step_index: int
    engine_name: str
    action: str
    status: str = "COMPLETED"  # "COMPLETED", "SKIPPED", "WARNED", "FAILED"
    duration_ms: float = 0.0
    decisions_made: int = 0
    message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "engine_name": self.engine_name,
            "action": self.action,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "decisions_made": self.decisions_made,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass
class PlanningTrace:
    correlation_id: str
    steps: List[PlanningTraceStep] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def add_step(self, step: PlanningTraceStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "steps": [s.to_dict() for s in self.steps],
        }
