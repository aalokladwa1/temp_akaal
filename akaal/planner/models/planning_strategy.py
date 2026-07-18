"""
Akaal — Enterprise Planning Strategy Model
==========================================
Deterministic planning strategy model for MigrationExecutionPlan.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class StrategyType(str, Enum):
    FULL_MIGRATION = "FULL_MIGRATION"
    PHASED_MIGRATION = "PHASED_MIGRATION"
    BLUE_GREEN_MIGRATION = "BLUE_GREEN_MIGRATION"
    ROLLING_MIGRATION = "ROLLING_MIGRATION"
    ZERO_DOWNTIME_MIGRATION = "ZERO_DOWNTIME_MIGRATION"
    BULK_CUTOVER = "BULK_CUTOVER"
    CUSTOM_STRATEGY = "CUSTOM_STRATEGY"


@dataclass
class PlanningStrategy:
    strategy_id: str = "strat_default"
    strategy_name: str = "Standard Full Migration Strategy"
    strategy_type: StrategyType = StrategyType.FULL_MIGRATION
    semantic_version: str = "1.0.0"
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_type": self.strategy_type.value if hasattr(self.strategy_type, "value") else str(self.strategy_type),
            "semantic_version": self.semantic_version,
            "parameters": self.parameters,
        }
