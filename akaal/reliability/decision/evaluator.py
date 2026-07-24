"""DecisionEvaluator for evaluating reliability decision choices."""

from enum import Enum
from akaal.reliability.decision.context import DecisionContext, ReliabilityRiskEvaluator


class ReliabilityDecisionChoice(str, Enum):
    RETRY = "RETRY"
    RECOVER = "RECOVER"
    ROLLBACK = "ROLLBACK"
    IGNORE = "IGNORE"
    ESCALATE = "ESCALATE"
    RESTART = "RESTART"
    DEGRADE = "DEGRADE"
    ABORT = "ABORT"


class DecisionEvaluator:
    """Evaluates whether to RETRY, RECOVER, ROLLBACK, IGNORE, ESCALATE, RESTART, DEGRADE, or ABORT."""

    def __init__(self):
        self.risk_evaluator = ReliabilityRiskEvaluator()

    def evaluate(self, ctx: DecisionContext) -> ReliabilityDecisionChoice:
        risk = self.risk_evaluator.evaluate_risk(ctx)

        if ctx.current_state == "Disaster" or risk > 95.0:
            return ReliabilityDecisionChoice.ABORT
        elif ctx.circuit_breaker_open:
            return ReliabilityDecisionChoice.DEGRADE
        elif risk > 80.0 and ctx.policy_profile in ("STRICT_FINANCE", "STRICT_HEALTHCARE"):
            return ReliabilityDecisionChoice.ESCALATE
        elif ctx.consecutive_errors > 5:
            return ReliabilityDecisionChoice.RESTART
        elif ctx.health_score < 60.0:
            return ReliabilityDecisionChoice.RECOVER
        elif ctx.consecutive_errors > 0:
            return ReliabilityDecisionChoice.RETRY
        else:
            return ReliabilityDecisionChoice.RETRY
