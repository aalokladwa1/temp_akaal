"""
Akaal — Validation Engine
========================
Single-responsibility engine validating rules against lifecycle state, capability requirements, and conditions.
"""

from typing import List, Tuple
from akaal.rulebook.models.rule import Rule, RuleLifecycleState
from akaal.rulebook.models.rule_condition import RuleConditionEvaluator
from akaal.rulebook.models.rule_evaluation_context import RuleEvaluationContext


class ValidationEngine:
    """Validates lifecycle state, required discovery sections, and rule conditions."""

    def validate_rules(self, rules: List[Rule], ctx: RuleEvaluationContext) -> Tuple[List[Rule], List[Rule], List[str]]:
        valid_rules: List[Rule] = []
        invalid_rules: List[Rule] = []
        reasons: List[str] = []

        report = ctx.discovery_report

        for rule in rules:
            # 1. Lifecycle State check
            if rule.lifecycle_state == RuleLifecycleState.RETIRED:
                invalid_rules.append(rule)
                reasons.append(f"Rule {rule.rule_id} rejected: Rule is RETIRED.")
                continue

            # 2. Required Scout Discovery Sections check
            req_sections = rule.capability_metadata.required_discovery_sections
            missing_section = False
            for sec in req_sections:
                if sec == "ClusterDiscovery" and not report.cluster_info:
                    missing_section = True
                elif sec == "StorageDiscovery" and not report.storage_inventory:
                    missing_section = True

            if missing_section:
                invalid_rules.append(rule)
                reasons.append(f"Rule {rule.rule_id} skipped: Required Scout section missing.")
                continue

            # 3. Rule Condition evaluation
            if rule.conditions and not RuleConditionEvaluator.evaluate_condition(rule.conditions, report):
                invalid_rules.append(rule)
                reasons.append(f"Rule {rule.rule_id} skipped: Condition evaluated to false.")
                continue

            valid_rules.append(rule)

        return valid_rules, invalid_rules, reasons
