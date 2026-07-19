"""
AKAAL Enterprise Intelligence Platform — Manifest Model
========================================================
Represents summary metadata manifest for an Enterprise Intelligence Model payload.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class EnterpriseIntelligenceManifest:
    """
    Immutable manifest detailing strategic intelligence summary metrics.
    """

    advisory_model_id: str
    total_decisions: int
    critical_decisions_count: int
    high_priority_decisions_count: int
    readiness_score: float
    simulated_downtime_p95_seconds: float
    generated_at_timestamp: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self,
                "metadata",
                MappingProxyType(dict(self.metadata) if self.metadata else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "advisory_model_id": self.advisory_model_id,
            "total_decisions": int(self.total_decisions),
            "critical_decisions_count": int(self.critical_decisions_count),
            "high_priority_decisions_count": int(self.high_priority_decisions_count),
            "readiness_score": float(self.readiness_score),
            "simulated_downtime_p95_seconds": float(self.simulated_downtime_p95_seconds),
            "generated_at_timestamp": self.generated_at_timestamp,
            "metadata": dict(self.metadata),
        }
