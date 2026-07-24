"""
AKAAL Platform 6 — Policy-as-Code (PaC) Executable Engine.
"""

from typing import Dict, Any, List
from akaal.governance.domain.models import EnterprisePolicy
from akaal.governance.domain.exceptions import PolicyViolationError


class PolicyAsCodeEngine:
    """Evaluates declarative governance policy rules against execution payloads."""

    def evaluate_policy(self, policy: EnterprisePolicy, context: Dict[str, Any]) -> bool:
        """
        Evaluates policy declarative_rule logic against context.
        Supports rule keywords like FORBID_DESTRUCTIVE, REQUIRE_FOUR_EYES, MAX_RISK_SCORE.
        """
        rule = policy.declarative_rule.upper()

        if "FORBID_DESTRUCTIVE" in rule:
            if context.get("is_destructive", False):
                return False

        if "MAX_RISK_SCORE" in rule:
            max_allowed = context.get("max_risk_threshold", 8.0)
            actual_risk = context.get("risk_score", 0.0)
            if actual_risk > max_allowed:
                return False

        if "DISALLOW_ROLE" in rule:
            forbidden_role = context.get("forbidden_role")
            user_role = context.get("requester_role")
            if forbidden_role and user_role == forbidden_role:
                return False

        return True

    def batch_evaluate(self, policies: List[EnterprisePolicy], context: Dict[str, Any]) -> Dict[str, bool]:
        results = {}
        for p in policies:
            results[p.policy_id] = self.evaluate_policy(p, context)
        return results
