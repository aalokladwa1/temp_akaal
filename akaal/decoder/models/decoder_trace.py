"""
Akaal — Decoder Execution Trace
===============================
Deterministic execution trace capturing step-by-step Decoder normalization flow.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TraceStep:
    normalization_order: int
    engine_name: str
    object_identifier: str
    status: str  # "NORMALIZED", "SKIPPED", "BLOCKED", "WARNED"
    datatype_mapped: bool = True
    metadata_mapped: bool = True
    expression_mapped: bool = True
    compatibility_resolved: bool = True
    validation_passed: bool = True
    duration_ms: float = 0.0
    warning_reason: Optional[str] = None
    skipped_reason: Optional[str] = None
    blocked_reason: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "normalization_order": self.normalization_order,
            "engine_name": self.engine_name,
            "object_identifier": self.object_identifier,
            "status": self.status,
            "datatype_mapped": self.datatype_mapped,
            "metadata_mapped": self.metadata_mapped,
            "expression_mapped": self.expression_mapped,
            "compatibility_resolved": self.compatibility_resolved,
            "validation_passed": self.validation_passed,
            "duration_ms": self.duration_ms,
            "warning_reason": self.warning_reason,
            "skipped_reason": self.skipped_reason,
            "blocked_reason": self.blocked_reason,
            "timestamp": self.timestamp,
        }


@dataclass
class DecoderExecutionTrace:
    """Deterministic trace log of Decoder pipeline execution."""
    correlation_id: str
    steps: List[TraceStep] = field(default_factory=list)
    total_trace_duration_ms: float = 0.0

    def add_step(self, step: TraceStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "total_trace_duration_ms": self.total_trace_duration_ms,
            "steps": [s.to_dict() for s in self.steps],
        }
