"""
Akaal — Inheritance Engine
==========================
Single-responsibility engine evaluating 8-level policy hierarchy overrides.
Hierarchy: Global -> Organization -> Project -> Migration -> Database -> Schema -> Table -> Column
"""

from typing import Dict, List, Tuple
from akaal.rulebook.models.rule import Rule, RuleScope
from akaal.rulebook.models.rule_result import RuleEvaluationResult
from akaal.rulebook.engine.priority_engine import SCOPE_PRECEDENCE


class InheritanceEngine:
    """Evaluates policy inheritance overrides deterministically."""

    def resolve_inheritance(self, rules: List[Rule]) -> Tuple[List[RuleEvaluationResult], Dict[str, Any]]:
        results: List[RuleEvaluationResult] = []
        category_map: Dict[str, List[Rule]] = {}

        for r in rules:
            cat = r.category.value if hasattr(r.category, "value") else str(r.category)
            category_map.setdefault(cat, []).append(r)

        inheritance_summary: Dict[str, Any] = {}

        for cat, cat_rules in category_map.items():
            # Sort by scope precedence (highest scope precedence wins)
            sorted_cat_rules = sorted(cat_rules, key=lambda r: SCOPE_PRECEDENCE.get(r.scope, 10), reverse=True)
            winning_rule = sorted_cat_rules[0]

            for r in sorted_cat_rules:
                if r.rule_id == winning_rule.rule_id:
                    results.append(RuleEvaluationResult(
                        rule_id=r.rule_id,
                        rule_name=r.name,
                        category=cat,
                        status="APPLIED",
                        scope=r.scope.value if hasattr(r.scope, "value") else str(r.scope),
                        provenance=r.provenance.value if hasattr(r.provenance, "value") else str(r.provenance),
                        rationale=f"Applied at scope {r.scope}.",
                        action_payload=r.action_payload,
                    ))
                else:
                    results.append(RuleEvaluationResult(
                        rule_id=r.rule_id,
                        rule_name=r.name,
                        category=cat,
                        status="OVERRIDDEN",
                        scope=r.scope.value if hasattr(r.scope, "value") else str(r.scope),
                        provenance=r.provenance.value if hasattr(r.provenance, "value") else str(r.provenance),
                        rationale=f"Overridden by rule {winning_rule.rule_id} at scope {winning_rule.scope}.",
                        override_rule_id=winning_rule.rule_id,
                    ))

            inheritance_summary[cat] = {
                "active_rule_id": winning_rule.rule_id,
                "active_scope": winning_rule.scope.value if hasattr(winning_rule.scope, "value") else str(winning_rule.scope),
                "overridden_count": len(sorted_cat_rules) - 1,
            }

        return results, inheritance_summary
