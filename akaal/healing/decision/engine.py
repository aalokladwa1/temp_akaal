"""DecisionEngine: Primary decision entry point prior to any repair operation."""

import logging
from typing import Any, Dict
from akaal.healing.decision.evaluator import DecisionEvaluator, RepairDecisionChoice
from akaal.healing.decision.context import DecisionContext

logger = logging.getLogger("akaal.healing.decision.engine")


class DecisionEngine:
    """Canonical Decision Engine evaluated before executing any self-healing action."""

    def __init__(self):
        self.evaluator = DecisionEvaluator()

    def make_decision(self, context: DecisionContext) -> RepairDecisionChoice:
        """Evaluate decision for a target repair action."""
        choice = self.evaluator.evaluate(context)
        logger.info(f"DecisionEngine choice: {choice.value} (Risk score evaluated)")
        return choice
