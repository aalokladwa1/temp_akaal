"""
Akaal — Advisory Evidence
=========================
Immutable evidence record supporting an advisory recommendation.
Enforces deep immutability via MappingProxyType.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class AdvisoryEvidence:
    """Immutable evidence backing a recommendation."""
    source_component: str
    metric_name: str
    observed_value: Any
    threshold_value: Any
    evidence_details: Mapping[str, Any] = field(default_factory=dict)
    references: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if isinstance(self.evidence_details, dict):
            object.__setattr__(self, "evidence_details", MappingProxyType(dict(self.evidence_details)))

    def to_dict(self) -> dict:
        return {
            "source_component": self.source_component,
            "metric_name": self.metric_name,
            "observed_value": self.observed_value,
            "threshold_value": self.threshold_value,
            "evidence_details": dict(self.evidence_details),
            "references": list(self.references),
        }
