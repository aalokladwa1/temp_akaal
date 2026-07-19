"""
AKAAL Enterprise Intelligence Platform — Strategy Synthesis Model
==================================================================
Represents synthesized enterprise migration strategy archetypes and trade-offs.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple
from akaal.intelligence.models.enterprise_intelligence_enums import StrategyType


@dataclass(frozen=True)
class StrategySynthesis:
    """
    Immutable representation of synthesized strategic migration strategy.
    """

    strategy_id: str
    strategy_type: StrategyType
    primary_objective: str
    recommended_execution_mode: str
    estimated_total_duration_seconds: float
    max_recommended_parallelism: int
    key_assumptions: Tuple[str, ...] = field(default_factory=tuple)
    strategic_advantages: Tuple[str, ...] = field(default_factory=tuple)
    identified_constraints: Tuple[str, ...] = field(default_factory=tuple)
    mitigation_guidelines: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.key_assumptions, tuple):
            object.__setattr__(self, "key_assumptions", tuple(self.key_assumptions))
        if not isinstance(self.strategic_advantages, tuple):
            object.__setattr__(self, "strategic_advantages", tuple(self.strategic_advantages))
        if not isinstance(self.identified_constraints, tuple):
            object.__setattr__(self, "identified_constraints", tuple(self.identified_constraints))
        if not isinstance(self.mitigation_guidelines, tuple):
            object.__setattr__(self, "mitigation_guidelines", tuple(self.mitigation_guidelines))

        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self,
                "metadata",
                MappingProxyType(dict(self.metadata) if self.metadata else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type.value if hasattr(self.strategy_type, "value") else str(self.strategy_type),
            "primary_objective": self.primary_objective,
            "recommended_execution_mode": self.recommended_execution_mode,
            "estimated_total_duration_seconds": float(self.estimated_total_duration_seconds),
            "max_recommended_parallelism": int(self.max_recommended_parallelism),
            "key_assumptions": list(self.key_assumptions),
            "strategic_advantages": list(self.strategic_advantages),
            "identified_constraints": list(self.identified_constraints),
            "mitigation_guidelines": list(self.mitigation_guidelines),
            "metadata": dict(self.metadata),
        }
