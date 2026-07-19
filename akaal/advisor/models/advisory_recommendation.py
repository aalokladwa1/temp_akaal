"""
Akaal — Advisory Recommendation
================================
Immutable recommendation dataclass produced by analyzers and processed by Aggregation.
Enforces deep immutability via MappingProxyType.
"""

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple

from akaal.advisor.models.advisory_decision import AdvisoryDecision
from akaal.advisor.models.advisory_enums import (
    AdvisoryCategory,
    AdvisoryPriority,
    AdvisorySeverity,
)
from akaal.advisor.models.advisory_evidence import AdvisoryEvidence


@dataclass(frozen=True)
class AdvisoryRecommendation:
    """Immutable recommendation model."""
    recommendation_id: str
    title: str
    category: AdvisoryCategory
    severity: AdvisorySeverity
    priority: AdvisoryPriority
    description: str
    rationale: str
    impact: str
    action_items: Tuple[str, ...] = field(default_factory=tuple)
    affected_nodes: Tuple[str, ...] = field(default_factory=tuple)
    evidence: Tuple[AdvisoryEvidence, ...] = field(default_factory=tuple)
    decision: Optional[AdvisoryDecision] = None
    fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.fingerprint:
            raw = f"{self.category.value if hasattr(self.category, 'value') else self.category}:{self.title}:{','.join(sorted(self.affected_nodes))}"
            fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            object.__setattr__(self, "fingerprint", fp)
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "category": self.category.value if isinstance(self.category, AdvisoryCategory) else str(self.category),
            "severity": self.severity.value if isinstance(self.severity, AdvisorySeverity) else str(self.severity),
            "priority": self.priority.value if isinstance(self.priority, AdvisoryPriority) else str(self.priority),
            "description": self.description,
            "rationale": self.rationale,
            "impact": self.impact,
            "action_items": list(self.action_items),
            "affected_nodes": list(self.affected_nodes),
            "evidence": [ev.to_dict() for ev in self.evidence],
            "decision": self.decision.to_dict() if self.decision else None,
            "fingerprint": self.fingerprint,
            "metadata": dict(self.metadata),
            "tags": list(self.tags),
        }
