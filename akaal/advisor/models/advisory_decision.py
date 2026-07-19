"""
Akaal — Advisory Decision
=========================
Immutable decision lineage object tracking decision rationale and risk mitigation.
Enforces deep immutability via MappingProxyType.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class AdvisoryDecision:
    """Immutable decision lineage for a recommendation."""
    decision_id: str
    recommendation_id: str
    rationale: str
    impact_analysis: str
    risk_mitigation: str
    alternatives_considered: Tuple[str, ...] = field(default_factory=tuple)
    lineage: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.lineage, dict):
            object.__setattr__(self, "lineage", MappingProxyType(dict(self.lineage)))

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "recommendation_id": self.recommendation_id,
            "rationale": self.rationale,
            "impact_analysis": self.impact_analysis,
            "risk_mitigation": self.risk_mitigation,
            "alternatives_considered": list(self.alternatives_considered),
            "lineage": dict(self.lineage),
        }
