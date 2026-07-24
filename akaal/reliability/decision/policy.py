"""DecisionPolicy for reliability decision constraints."""

from typing import Dict, Any
from akaal.reliability.decision.context import DecisionContext


class DecisionPolicy:
    """Enforces policy constraints on decision evaluator choices."""

    def apply_policy(self, choice_str: str, ctx: DecisionContext) -> str:
        if ctx.policy_profile == "STRICT_FINANCE" and choice_str == "DEGRADE":
            # Mandatory escalation for degraded mode under finance policy
            return "ESCALATE"
        return choice_str
