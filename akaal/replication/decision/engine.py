"""ReplicationDecisionEngine: Primary entry point evaluating all replication choices."""

import logging
from akaal.replication.decision.evaluator import DecisionEvaluator, ReplicationDecisionChoice
from akaal.replication.decision.context import DecisionContext
from akaal.replication.decision.policy import DecisionPolicy

logger = logging.getLogger("akaal.replication.decision.engine")


class ReplicationDecisionEngine:
    """Canonical Replication Decision Engine evaluated before executing any replication task."""

    def __init__(self):
        self.evaluator = DecisionEvaluator()
        self.policy = DecisionPolicy()

    def make_decision(self, context: DecisionContext) -> ReplicationDecisionChoice:
        """Evaluate decision for a target replication action."""
        choice = self.evaluator.evaluate(context)
        final_choice_str = self.policy.apply_policy(choice.value, context)
        final_choice = ReplicationDecisionChoice(final_choice_str)
        logger.info(f"ReplicationDecisionEngine choice: {final_choice.value}")
        return final_choice
