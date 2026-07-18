"""
Akaal — Planner Registry & Strategy Registry
=============================================
Thread-safe registries for planning strategies with governance metadata.
"""

import hashlib
import threading
from typing import Any, Dict, List, Optional
from akaal.planner.models.planning_strategy import PlanningStrategy, StrategyType


class StrategyRegistry:
    """Strategy registry with governance metadata validation."""

    _DEFAULT_STRATEGIES = {
        s.value: {
            "strategy_id": s.value.lower(),
            "strategy_name": s.value.replace("_", " ").title(),
            "strategy_type": s.value,
            "semantic_version": "1.0.0",
            "lifecycle_state": "ACTIVE",
            "supported_planner_schema": "1.0.0",
            "supported_risk_schema": "1.0.0",
        }
        for s in StrategyType
    }

    @classmethod
    def get_strategy_metadata(cls, strategy_type: str) -> Optional[Dict[str, Any]]:
        return cls._DEFAULT_STRATEGIES.get(strategy_type)

    @classmethod
    def list_strategies(cls) -> List[Dict[str, Any]]:
        return list(cls._DEFAULT_STRATEGIES.values())


class PlannerRegistry:
    """Thread-safe registry for Planner strategies with governance validation."""

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def validate_strategy(self, strategy: PlanningStrategy) -> bool:
        meta = StrategyRegistry.get_strategy_metadata(
            strategy.strategy_type.value if hasattr(strategy.strategy_type, "value") else str(strategy.strategy_type)
        )
        return meta is not None and meta.get("lifecycle_state") == "ACTIVE"

    def list_strategies(self) -> List[Dict[str, Any]]:
        with self._lock:
            return StrategyRegistry.list_strategies()
