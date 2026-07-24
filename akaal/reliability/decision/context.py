"""Decision Context and Risk Evaluator for Reliability Decision Engine."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class DecisionContext:
    """Contextual metrics evaluated before executing reliability operations."""

    health_score: float = 100.0
    failure_count: int = 0
    consecutive_errors: int = 0
    sla_availability_pct: float = 99.99
    current_state: str = "Healthy"
    policy_profile: str = "ENTERPRISE"
    component_name: str = "database_pool"
    circuit_breaker_open: bool = False
    is_critical_path: bool = True


class ReliabilityRiskEvaluator:
    """Computes risk score (0.0 to 100.0) for reliability decision making."""

    def evaluate_risk(self, ctx: DecisionContext) -> float:
        risk = 5.0
        if ctx.health_score < 80.0:
            risk += 30.0
        if ctx.consecutive_errors > 3:
            risk += 25.0
        if ctx.circuit_breaker_open:
            risk += 30.0
        if ctx.is_critical_path:
            risk += 10.0
        return min(risk, 100.0)
