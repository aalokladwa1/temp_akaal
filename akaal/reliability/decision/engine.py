"""ReliabilityDecisionEngine: Centralized Decision Engine for Platform 4."""

import logging
from akaal.reliability.decision.evaluator import DecisionEvaluator, ReliabilityDecisionChoice
from akaal.reliability.decision.context import DecisionContext
from akaal.reliability.decision.policy import DecisionPolicy

logger = logging.getLogger("akaal.reliability.decision.engine")


class ReliabilityDecisionEngine:
    """Canonical Reliability Decision Engine evaluating action choices before execution."""

    def __init__(self):
        self.evaluator = DecisionEvaluator()
        self.policy = DecisionPolicy()

    def make_decision(self, context: DecisionContext) -> ReliabilityDecisionChoice:
        choice = self.evaluator.evaluate(context)
        final_choice_str = self.policy.apply_policy(choice.value, context)
        final_choice = ReliabilityDecisionChoice(final_choice_str)
        logger.info(f"ReliabilityDecisionEngine choice: {final_choice.value}")
        return final_choice
