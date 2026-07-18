"""
Akaal — Rule Execution Trace
============================
Deterministic execution trace capturing step-by-step Rulebook evaluation flow.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TraceStep:
    evaluation_order: int
    engine_name: str
    rule_id: str
    decision: str  # "APPLIED", "SKIPPED", "BLOCKED", "OVERRIDDEN", "REJECTED"
    dependency_resolved: bool = True
    priority_score: int = 100
    inheritance_scope: str = "GLOBAL"
    capability_validated: bool = True
    lifecycle_validated: bool = True
    conflict_detected: bool = False
    duration_ms: float = 0.0
    applied_reason: Optional[str] = None
    skipped_reason: Optional[str] = None
    blocked_reason: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_order": self.evaluation_order,
            "engine_name": self.engine_name,
            "rule_id": self.rule_id,
            "decision": self.decision,
            "dependency_resolved": self.dependency_resolved,
            "priority_score": self.priority_score,
            "inheritance_scope": self.inheritance_scope,
            "capability_validated": self.capability_validated,
            "lifecycle_validated": self.lifecycle_validated,
            "conflict_detected": self.conflict_detected,
            "duration_ms": self.duration_ms,
            "applied_reason": self.applied_reason,
            "skipped_reason": self.skipped_reason,
            "blocked_reason": self.blocked_reason,
            "timestamp": self.timestamp,
        }


@dataclass
class RuleExecutionTrace:
    """Deterministic trace log of Rulebook pipeline execution."""
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
