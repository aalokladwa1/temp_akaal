"""
Akaal — Rule Condition Evaluator
================================
Evaluates conditional expressions for Rule activation.
"""

from typing import Any, Dict
from akaal.scout.models.discovery_report import DiscoveryReport


class RuleConditionEvaluator:
    """Evaluates IF-THEN rule conditions against DiscoveryReport metadata."""

    @staticmethod
    def evaluate_condition(condition: Dict[str, Any], report: DiscoveryReport) -> bool:
        if not condition:
            return True

        # Field matchers
        target_field = condition.get("field")
        op = condition.get("operator", "==")
        target_val = condition.get("value")

        if target_field == "table_count":
            actual_val = report.statistics.total_tables
        elif target_field == "database_size_bytes":
            actual_val = report.statistics.total_bytes
        elif target_field == "system_type":
            actual_val = report.engine_info.system_type
        else:
            return True

        if op == "==":
            return actual_val == target_val
        elif op == "!=":
            return actual_val != target_val
        elif op == ">":
            return actual_val > target_val
        elif op == ">=":
            return actual_val >= target_val
        elif op == "<":
            return actual_val < target_val
        elif op == "<=":
            return actual_val <= target_val
        elif op == "in":
            return actual_val in target_val
        return True
