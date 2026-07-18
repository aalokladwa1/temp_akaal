"""
Akaal — Planning Context
========================
Immutable execution context passed to planning engines and analyzers in Planner Platform.
Wraps RiskAssessmentModel without consuming any Rulebook, Decoder, or Scout runtime components.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from akaal.risk.models.risk_assessment_model import RiskAssessmentModel
from akaal.planner.models.planning_strategy import PlanningStrategy, StrategyType
from akaal.planner.models.execution_constraint import ExecutionConstraints


@dataclass(frozen=True)
class PlanningContext:
    """Immutable planning context wrapping RiskAssessmentModel."""
    risk_model: RiskAssessmentModel
    strategy: PlanningStrategy = field(default_factory=PlanningStrategy)
    constraints: ExecutionConstraints = field(default_factory=ExecutionConstraints)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    configuration: Dict[str, Any] = field(default_factory=dict)
    planner_schema_version: str = "1.0.0"
    simulation_mode: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
