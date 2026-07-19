"""
Akaal — Advisory Trace
======================
Immutable execution trace capturing timing, analyzer steps, lineage, and diagnostics.
Enforces deep immutability via MappingProxyType.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class AdvisoryTrace:
    """Immutable trace data recording execution metrics and diagnostic logs."""
    trace_id: str
    execution_duration_ms: float
    analyzer_traces: Tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    lineage_graph: Mapping[str, Any] = field(default_factory=dict)
    diagnostic_logs: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.lineage_graph, dict):
            object.__setattr__(self, "lineage_graph", MappingProxyType(dict(self.lineage_graph)))

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "execution_duration_ms": self.execution_duration_ms,
            "analyzer_traces": [dict(t) for t in self.analyzer_traces],
            "lineage_graph": dict(self.lineage_graph),
            "diagnostic_logs": list(self.diagnostic_logs),
        }
