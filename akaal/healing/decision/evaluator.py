"""DecisionEvaluator for evaluating self-healing choices."""

from enum import Enum
from typing import Dict, Any
from akaal.healing.decision.context import DecisionContext, RiskEvaluator


class RepairDecisionChoice(str, Enum):
    REPAIR = "REPAIR"
    RETRY = "RETRY"
    ROLLBACK = "ROLLBACK"
    ESCALATE = "ESCALATE"
    WAIT = "WAIT"
    IGNORE = "IGNORE"


class DecisionEvaluator:
    """Evaluates whether to REPAIR, RETRY, ROLLBACK, ESCALATE, WAIT, or IGNORE."""

    def __init__(self):
        self.risk_evaluator = RiskEvaluator()

    def evaluate(self, ctx: DecisionContext) -> RepairDecisionChoice:
        """Determine optimal repair decision."""
        risk = self.risk_evaluator.evaluate_risk(ctx)

        if risk > 80.0 and ctx.policy_profile == "STRICT_FINANCE":
            return RepairDecisionChoice.ESCALATE
        elif risk > 90.0:
            return RepairDecisionChoice.ROLLBACK
        elif ctx.confidence_score < 70.0:
            return RepairDecisionChoice.RETRY
        else:
            return RepairDecisionChoice.REPAIR
