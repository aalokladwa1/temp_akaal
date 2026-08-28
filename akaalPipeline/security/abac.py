"""akaalPipeline.security.abac
============================
Canonical Typed ABAC Policy Engine with deterministic JSON expression evaluation and fail-closed missing attributes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from akaalPipeline.contracts.enums import PolicyEffect
from akaalPipeline.state.repositories import SQLiteABACPolicyRepository


class MissingAttributeError(ValueError):
    """Raised when an ABAC condition requires an attribute that is missing from context."""
    pass


class ABACAuthority:
    """Canonical typed ABAC policy evaluator."""

    def __init__(self, policy_repo: SQLiteABACPolicyRepository) -> None:
        self.policy_repo = policy_repo

    def _resolve_attribute(self, attr_path: str, context: Dict[str, Any]) -> Any:
        """Resolve dotted attribute path from context dictionary. Fails closed if missing."""
        parts = attr_path.split(".")
        curr = context
        for part in parts:
            if not isinstance(curr, dict) or part not in curr:
                raise MissingAttributeError(f"Missing mandatory ABAC attribute: {attr_path!r}")
            curr = curr[part]
        return curr

    def _evaluate_expression(self, expr: Any, context: Dict[str, Any]) -> bool:
        """Recursively evaluate typed boolean expression against context."""
        if isinstance(expr, bool):
            return expr
        if not isinstance(expr, dict):
            raise ValueError(f"Invalid condition expression format: {expr!r}")

        for op, args in expr.items():
            if op == "and":
                if not isinstance(args, list):
                    raise ValueError("'and' expression requires a list")
                return all(self._evaluate_expression(sub, context) for sub in args)
            elif op == "or":
                if not isinstance(args, list):
                    raise ValueError("'or' expression requires a list")
                return any(self._evaluate_expression(sub, context) for sub in args)
            elif op == "not":
                return not self._evaluate_expression(args, context)
            elif op == "equals":
                if isinstance(args, dict):
                    k, expected = next(iter(args.items()))
                    val = self._resolve_attribute(k, context)
                elif isinstance(args, list) and len(args) == 2:
                    val = self._resolve_attribute(args[0], context) if isinstance(args[0], str) and "." in args[0] else args[0]
                    expected = self._resolve_attribute(args[1], context) if isinstance(args[1], str) and "." in args[1] else args[1]
                else:
                    raise ValueError("'equals' expression requires [attr_path, expected_value] or {attr_path: expected_value}")
                if type(val) != type(expected) and not (isinstance(val, (int, float)) and isinstance(expected, (int, float))):
                    return False
                return val == expected
            elif op == "in":
                if not isinstance(args, list) or len(args) != 2:
                    raise ValueError("'in' expression requires [attr_path, list_of_values]")
                val = self._resolve_attribute(args[0], context) if isinstance(args[0], str) and "." in args[0] else args[0]
                container = args[1]
                if not isinstance(container, list):
                    raise ValueError("Second argument to 'in' must be a list")
                return val in container
            elif op == "greater_than":
                if not isinstance(args, list) or len(args) != 2:
                    raise ValueError("'greater_than' requires [attr_path, threshold]")
                val = self._resolve_attribute(args[0], context)
                thresh = args[1]
                return val > thresh
            else:
                raise ValueError(f"Unknown ABAC operator: {op!r}")

        return False

    def evaluate_policies(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        context: Dict[str, Any],
    ) -> PolicyEffect:
        """
        Evaluate active policies in priority order.
        When no ABAC policies match or exist, returns ALLOW (leaving authorization to RBAC).
        Deny overrides allow. Missing attributes fail closed (DENY).
        """
        policies = self.policy_repo.list_active_policies(tenant_id)
        if not policies:
            return PolicyEffect.ALLOW

        applicable_allow_policies = False
        has_allow = False

        for policy in policies:
            # Check target match
            if policy["target_action"] != "*" and policy["target_action"] != action:
                continue
            if policy["target_resource_type"] != "*" and policy["target_resource_type"] != resource_type:
                continue

            if policy["effect"] == PolicyEffect.ALLOW.value:
                applicable_allow_policies = True

            try:
                matches = self._evaluate_expression(policy["condition_expression"], context)
            except MissingAttributeError:
                matches = False

            if matches:
                if policy["effect"] == PolicyEffect.DENY.value:
                    return PolicyEffect.DENY
                elif policy["effect"] == PolicyEffect.ALLOW.value:
                    has_allow = True

        if applicable_allow_policies:
            return PolicyEffect.ALLOW if has_allow else PolicyEffect.DENY

        return PolicyEffect.ALLOW

    def evaluate(self, tenant_id: str, action: str, attributes: Dict[str, Any], resource_type: str = "*") -> str:
        """Convenience evaluation returning effect string ('ALLOW' or 'DENY')."""
        effect = self.evaluate_policies(tenant_id, action, resource_type, attributes)
        return effect.value if hasattr(effect, "value") else str(effect)
