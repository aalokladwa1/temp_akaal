"""
AKAAL Platform 6 — Compliance Rule Engine.
"""

from typing import Dict, List, Any, Tuple
from akaal.governance.domain.models import ComplianceRule


class ComplianceRuleEngine:
    """Evaluates governance operations against regulatory controls (SOC2, HIPAA, GDPR, ISO27001)."""

    def __init__(self) -> None:
        self._rules: Dict[str, ComplianceRule] = {}

    def register_rule(self, rule: ComplianceRule) -> None:
        self._rules[rule.rule_id] = rule

    def evaluate_compliance(self, payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        violations = []
        for r in self._rules.values():
            if "REQUIRE_AUDIT_LOG" in r.validation_logic and not payload.get("audit_enabled", True):
                violations.append(f"Compliance violation ({r.standard_name} - {r.regulation_code}): Audit log is disabled.")
            if "REQUIRE_ENCRYPTION" in r.validation_logic and not payload.get("encrypted", True):
                violations.append(f"Compliance violation ({r.standard_name} - {r.regulation_code}): Data payload not encrypted.")
        return len(violations) == 0, violations
