"""
Akaal — Planner Platform Public API
=====================================
Public API for enterprise migration execution planning.
Consumes exclusively RiskAssessmentModel from Risk Platform and outputs MigrationExecutionPlan.
Contains zero SQL generation, zero migration execution, zero database connections.
"""

import time
import logging
from typing import Any, Dict, Optional

from akaal.risk.models.risk_assessment_model import RiskAssessmentModel
from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.planning_strategy import PlanningStrategy, StrategyType
from akaal.planner.models.execution_constraint import ExecutionConstraints
from akaal.planner.engine.planning_pipeline import PlanningPipeline
from akaal.planner.reporting.planner_report_builder import PlannerReportBuilder
from akaal.planner.registry.planner_registry import PlannerRegistry

logger = logging.getLogger("akaal.planner")


class PlannerPlatform:
    """
    Public entry point for Planner Platform.
    Builds a deterministic, immutable MigrationExecutionPlan from RiskAssessmentModel.
    """

    @classmethod
    def build_execution_plan(
        cls,
        risk_model: RiskAssessmentModel,
        strategy: Optional[PlanningStrategy] = None,
        constraints: Optional[ExecutionConstraints] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> MigrationExecutionPlan:
        """
        Single deterministic entry point for Planner Platform.
        Returns an immutable MigrationExecutionPlan.
        """
        t0 = time.time()

        strategy = strategy or PlanningStrategy()
        constraints = constraints or ExecutionConstraints()

        # Validate strategy governance
        registry = PlannerRegistry()
        if not registry.validate_strategy(strategy):
            logger.warning(f"Strategy {strategy.strategy_type} is not in ACTIVE lifecycle state.")

        ctx = PlanningContext(
            risk_model=risk_model,
            strategy=strategy,
            constraints=constraints,
            configuration=configuration or {},
        )

        pipeline = PlanningPipeline()
        plan = pipeline.run(ctx)
        plan = PlannerReportBuilder.finalize(plan)

        elapsed_ms = (time.time() - t0) * 1000
        logger.debug(f"[PlannerPlatform] plan built in {elapsed_ms:.2f}ms. checksum={plan.sha256_checksum[:16]}...")

        return plan


def build_execution_plan(
    risk_model: RiskAssessmentModel,
    strategy: Optional[PlanningStrategy] = None,
    constraints: Optional[ExecutionConstraints] = None,
    configuration: Optional[Dict[str, Any]] = None,
) -> MigrationExecutionPlan:
    """Top-level helper function for Planner Platform."""
    return PlannerPlatform.build_execution_plan(
        risk_model=risk_model,
        strategy=strategy,
        constraints=constraints,
        configuration=configuration,
    )
