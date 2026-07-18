"""
Akaal — Risk Execution Trace
============================
Deterministic execution trace capturing step-by-step Risk analysis pipeline flow.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class RiskTraceStep:
    analysis_order: int
    analyzer_or_engine_name: str
    target_object_id: str
    status: str  # "ANALYZED", "SKIPPED", "WARNED", "FAILED"
    duration_ms: float = 0.0
    detected_risks_count: int = 0
    message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_order": self.analysis_order,
            "analyzer_or_engine_name": self.analyzer_or_engine_name,
            "target_object_id": self.target_object_id,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "detected_risks_count": self.detected_risks_count,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass
class RiskExecutionTrace:
    """Deterministic trace log of Risk pipeline execution."""
    correlation_id: str
    steps: List[RiskTraceStep] = field(default_factory=list)
    total_trace_duration_ms: float = 0.0

    def add_step(self, step: RiskTraceStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "total_trace_duration_ms": round(self.total_trace_duration_ms, 2),
            "steps": [s.to_dict() for s in self.steps],
        }
