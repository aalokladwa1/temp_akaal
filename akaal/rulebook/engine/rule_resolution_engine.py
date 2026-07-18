"""
Akaal — Rule Resolution Engine
==============================
Single-responsibility engine for matching candidate rules against target engine & metadata.
"""

from typing import List
from akaal.rulebook.models.rule import Rule
from akaal.rulebook.models.rule_evaluation_context import RuleEvaluationContext


class RuleResolutionEngine:
    """Matches candidate rules against DiscoveryReport and target engine specification."""

    def resolve_candidate_rules(self, ctx: RuleEvaluationContext) -> List[Rule]:
        if not ctx.rule_registry_ref:
            return []

        all_rules = ctx.rule_registry_ref.get_all_rules()
        candidates: List[Rule] = []

        target_engine = ctx.target_engine.upper()

        for rule in all_rules:
            supported = rule.capability_metadata.supported_engines
            if "*" in supported or target_engine in [s.upper() for s in supported]:
                candidates.append(rule)

        return candidates
