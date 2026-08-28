"""
AKAAL Platform 6 — Separation of Duties (SoD) Engine.
"""

from typing import List, Dict, Tuple, Optional
from akaal.governance.domain.models import SoDRule
from akaal.governance.domain.exceptions import SoDViolationError


class SeparationOfDutiesEngine:
    """Enforces organizational SoD matrices and prevents self-approval or conflicting roles."""

    def __init__(self) -> None:
        self._rules: Dict[str, SoDRule] = {
            "sod-default-01": SoDRule(
                rule_id="sod-default-01",
                role_a="MigrationRequester",
                role_b="MigrationApprover",
                description="Requester and Approver roles are mutually exclusive",
            )
        }

    def register_rule(self, rule: SoDRule) -> None:
        self._rules[rule.rule_id] = rule

    def validate_approval(self, requester_id: str, approver_ids: List[str], requester_role: str, approver_roles: List[str]) -> Tuple[bool, List[str]]:
        violations = []

        # 1. Self Approval Prevention
        if requester_id in approver_ids:
            violations.append(f"Self-approval detected: User '{requester_id}' cannot approve their own request.")

        # 2. Conflicting Role Check
        for rule in self._rules.values():
            if not rule.is_active:
                continue
            if requester_role == rule.role_a and rule.role_b in approver_roles:
                violations.append(f"SoD Conflict (Rule {rule.rule_id}): Requester role '{requester_role}' conflicts with approver role '{rule.role_b}'.")
        return len(violations) == 0, violations

    def validate_assignments(self, principal_id: str, assigned_roles: List[str]) -> Tuple[bool, List[str]]:
        """Validate if a principal's set of assigned roles violates static mutually exclusive role definitions."""
        violations = []
        for rule in self._rules.values():
            if not rule.is_active:
                continue
            if rule.role_a in assigned_roles and rule.role_b in assigned_roles:
                violations.append(f"SoD Conflict (Rule {rule.rule_id}): Principal '{principal_id}' cannot hold both '{rule.role_a}' and '{rule.role_b}'.")
        return len(violations) == 0, violations
