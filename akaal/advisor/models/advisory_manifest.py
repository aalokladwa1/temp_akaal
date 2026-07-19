"""
Akaal — Advisory Manifest
=========================
Immutable summary manifest of an advisory model execution.
Enforces deep immutability via MappingProxyType.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class AdvisoryManifest:
    """Immutable advisory manifest summarizing recommendations by category, severity, priority."""
    advisory_id: str
    plan_id: str
    plan_checksum: str
    total_recommendations: int
    summary_by_category: Mapping[str, int] = field(default_factory=dict)
    summary_by_severity: Mapping[str, int] = field(default_factory=dict)
    summary_by_priority: Mapping[str, int] = field(default_factory=dict)
    creation_timestamp: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.summary_by_category, dict):
            object.__setattr__(self, "summary_by_category", MappingProxyType(dict(self.summary_by_category)))
        if isinstance(self.summary_by_severity, dict):
            object.__setattr__(self, "summary_by_severity", MappingProxyType(dict(self.summary_by_severity)))
        if isinstance(self.summary_by_priority, dict):
            object.__setattr__(self, "summary_by_priority", MappingProxyType(dict(self.summary_by_priority)))

    def to_dict(self) -> dict:
        return {
            "advisory_id": self.advisory_id,
            "plan_id": self.plan_id,
            "plan_checksum": self.plan_checksum,
            "total_recommendations": self.total_recommendations,
            "summary_by_category": dict(self.summary_by_category),
            "summary_by_severity": dict(self.summary_by_severity),
            "summary_by_priority": dict(self.summary_by_priority),
            "creation_timestamp": self.creation_timestamp,
        }
