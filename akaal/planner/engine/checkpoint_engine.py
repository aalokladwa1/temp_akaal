"""
Akaal — Checkpoint Engine
==========================
Generates CheckpointPlan with checkpoint locations, frequency, and recovery boundaries.
"""

from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.checkpoint_plan import CheckpointPlan, CheckpointLocation
from akaal.planner.analyzers.checkpoint_analyzer import CheckpointAnalyzer


class CheckpointEngine:
    """Generates checkpoint strategy for MigrationExecutionPlan."""

    def build_checkpoint_plan(self, ctx: PlanningContext) -> CheckpointPlan:
        analyzer = CheckpointAnalyzer()
        locations = analyzer.analyze(ctx)

        resume_points = [loc.checkpoint_id for loc in locations]
        validation_gates = [loc.checkpoint_id for loc in locations if "STAGE" in loc.checkpoint_id]

        return CheckpointPlan(
            strategy="STAGE_BOUNDARY",
            frequency="AFTER_EACH_STAGE",
            locations=locations,
            resume_points=resume_points,
            validation_gates=validation_gates,
        )
