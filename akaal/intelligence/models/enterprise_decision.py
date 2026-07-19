"""
AKAAL Enterprise Intelligence Platform — Enterprise Decision Model
===================================================================
Represents a synthesized enterprise-level migration decision produced by the
Decision Graph Engine.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple
from akaal.intelligence.models.enterprise_intelligence_enums import DecisionPriority, RiskLevel


@dataclass(frozen=True)
class EnterpriseDecision:
    """
    Immutable representation of a strategic migration decision.
    """

    decision_id: str
    title: str
    category: str
    priority: DecisionPriority
    risk_level: RiskLevel
    description: str
    rationale: str
    strategic_impact: str
    confidence_score: float  # 0.0 to 1.0
    action_items: Tuple[str, ...] = field(default_factory=tuple)
    trade_offs: Tuple[str, ...] = field(default_factory=tuple)
    affected_components: Tuple[str, ...] = field(default_factory=tuple)
    evidence_pointers: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Guarantee deep tuple immutability for sequence inputs
        if not isinstance(self.action_items, tuple):
            object.__setattr__(self, "action_items", tuple(self.action_items))
        if not isinstance(self.trade_offs, tuple):
            object.__setattr__(self, "trade_offs", tuple(self.trade_offs))
        if not isinstance(self.affected_components, tuple):
            object.__setattr__(self, "affected_components", tuple(self.affected_components))
        if not isinstance(self.evidence_pointers, tuple):
            object.__setattr__(self, "evidence_pointers", tuple(self.evidence_pointers))

        # Guarantee deep dict immutability via MappingProxyType
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self,
                "metadata",
                MappingProxyType(dict(self.metadata) if self.metadata else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "decision_id": self.decision_id,
            "title": self.title,
            "category": self.category,
            "priority": self.priority.value if hasattr(self.priority, "value") else str(self.priority),
            "risk_level": self.risk_level.value if hasattr(self.risk_level, "value") else str(self.risk_level),
            "description": self.description,
            "rationale": self.rationale,
            "strategic_impact": self.strategic_impact,
            "confidence_score": float(self.confidence_score),
            "action_items": list(self.action_items),
            "trade_offs": list(self.trade_offs),
            "affected_components": list(self.affected_components),
            "evidence_pointers": list(self.evidence_pointers),
            "metadata": dict(self.metadata),
        }
