"""
Akaal — Mitigation Strategy Model
=================================
Recommended mitigation strategies for detected risk items.
Risk produces strategies but NEVER executes them.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MitigationStrategy:
    strategy_id: str
    action_type: str  # "MANUAL_REVIEW", "FEATURE_EMULATION", "SCHEMA_ADJUSTMENT", "TRANSFORMATION_RULE", "ADDITIONAL_VALIDATION"
    description: str
    estimated_effort_hours: float = 1.0
    impact_reduction_percentage: float = 50.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "action_type": self.action_type,
            "description": self.description,
            "estimated_effort_hours": self.estimated_effort_hours,
            "impact_reduction_percentage": self.impact_reduction_percentage,
        }
