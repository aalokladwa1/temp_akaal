"""DecisionContext & RiskEvaluator for decision engine."""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class DecisionContext:
    """Contextual factors used to make self-healing decisions."""

    issue_severity: str = "ERROR"
    confidence_score: float = 100.0
    business_impact_level: str = "MEDIUM"
    policy_profile: str = "AUTOMATIC"
    historical_success_rate: float = 1.0
    is_dry_run: bool = False


class RiskEvaluator:
    """Evaluates risk levels for proposed repair actions."""

    def evaluate_risk(self, ctx: DecisionContext) -> float:
        """Return risk score (0 to 100)."""
        base_risk = 10.0
        if ctx.issue_severity == "CRITICAL":
            base_risk += 40.0
        if ctx.business_impact_level == "HIGH":
            base_risk += 30.0
        if ctx.confidence_score < 90.0:
            base_risk += 20.0
        return min(base_risk, 100.0)
