"""
Akaal — Priority Engine
=======================
Single-responsibility engine ordering validated rules by priority score and scope precedence.
"""

from typing import List
from akaal.rulebook.models.rule import Rule, RuleScope


SCOPE_PRECEDENCE = {
    RuleScope.COLUMN: 80,
    RuleScope.TABLE: 70,
    RuleScope.SCHEMA: 60,
    RuleScope.DATABASE: 50,
    RuleScope.MIGRATION: 40,
    RuleScope.PROJECT: 30,
    RuleScope.ORGANIZATION: 20,
    RuleScope.GLOBAL: 10,
}


class PriorityEngine:
    """Prioritizes rules according to priority score and scope precedence."""

    def prioritize_rules(self, rules: List[Rule]) -> List[Rule]:
        def _key(rule: Rule) -> tuple:
            scope_val = SCOPE_PRECEDENCE.get(rule.scope, 10)
            return (-scope_val, rule.priority, rule.rule_id)

        return sorted(rules, key=_key)
