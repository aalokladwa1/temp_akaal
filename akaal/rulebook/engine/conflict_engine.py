"""
Akaal — Conflict Engine
======================
Single-responsibility engine detecting duplicate/incompatible rules and producing enterprise diagnostics.
"""

from typing import Dict, List, Tuple
from akaal.rulebook.models.rule import Rule
from akaal.rulebook.models.rule_diagnostic import RuleDiagnostic, DiagnosticSeverity


class ConflictEngine:
    """Detects conflicting rule definitions and structural conflicts."""

    def detect_conflicts(self, rules: List[Rule]) -> Tuple[List[Rule], List[RuleDiagnostic]]:
        diagnostics: List[RuleDiagnostic] = []
        conflicting_ids = set()
        seen_ids: Dict[str, Rule] = {}

        for rule in rules:
            if rule.rule_id in seen_ids:
                conflicting_ids.add(rule.rule_id)
                diagnostics.append(RuleDiagnostic(
                    diagnostic_id=f"DIAG-DUP-{rule.rule_id}",
                    severity=DiagnosticSeverity.ERROR,
                    category="DUPLICATE_RULE",
                    affected_rules=[rule.rule_id],
                    root_cause=f"Duplicate rule identifier '{rule.rule_id}' detected.",
                    recommended_resolution="Ensure all rule IDs are unique across rule packs.",
                ))
            else:
                seen_ids[rule.rule_id] = rule

        # Filter out conflicting duplicate rules
        filtered = [r for r in rules if r.rule_id not in conflicting_ids]
        return filtered, diagnostics
