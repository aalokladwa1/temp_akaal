"""
AKAAL Enterprise Intelligence Platform — Execution Trace Model
===============================================================
Represents microsecond diagnostic execution metrics for Platform 2 intelligence pipeline runs.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class EnterpriseIntelligenceTrace:
    """
    Immutable execution trace capturing pipeline timing details and logs.
    """

    trace_id: str
    total_execution_duration_ms: float
    analyzer_durations_ms: Mapping[str, float] = field(default_factory=dict)
    decision_graph_duration_ms: float = 0.0
    evaluation_logs: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_logs, tuple):
            object.__setattr__(self, "evaluation_logs", tuple(self.evaluation_logs))

        if not isinstance(self.analyzer_durations_ms, MappingProxyType):
            object.__setattr__(
                self,
                "analyzer_durations_ms",
                MappingProxyType(dict(self.analyzer_durations_ms) if self.analyzer_durations_ms else {}),
            )
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self,
                "metadata",
                MappingProxyType(dict(self.metadata) if self.metadata else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "trace_id": self.trace_id,
            "total_execution_duration_ms": float(self.total_execution_duration_ms),
            "analyzer_durations_ms": dict(self.analyzer_durations_ms),
            "decision_graph_duration_ms": float(self.decision_graph_duration_ms),
            "evaluation_logs": list(self.evaluation_logs),
            "metadata": dict(self.metadata),
        }
