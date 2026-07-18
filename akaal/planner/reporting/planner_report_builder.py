"""
Akaal — Planner Report Builder
================================
Thin wrapper — AggregationEngine handles full assembly. This module provides
any post-assembly reporting enrichment.
"""

from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan
from akaal.planner.validation.planner_validator import PlannerValidator


class PlannerReportBuilder:
    """Enriches and validates a MigrationExecutionPlan after assembly."""

    @staticmethod
    def finalize(plan: MigrationExecutionPlan) -> MigrationExecutionPlan:
        # Validate the plan (raises no exception — returns warnings instead)
        warnings = PlannerValidator.validate_plan(plan)
        if warnings:
            import logging
            for w in warnings:
                logging.getLogger("akaal.planner").warning(w)
        return plan
