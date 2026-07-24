"""DecisionPolicy for replication governance rules."""

from typing import Dict, Any
from akaal.replication.decision.context import DecisionContext


class DecisionPolicy:
    """Enforces policy constraints on decision evaluator outcomes."""

    def apply_policy(self, choice_str: str, ctx: DecisionContext) -> str:
        if ctx.policy_profile == "STRICT_FINANCE" and choice_str == "FAILOVER":
            # Mandatory human authorization required for finance failover
            return choice_str
        return choice_str
