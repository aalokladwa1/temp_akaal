"""
Akaal — Rollback Engine
========================
Generates RollbackPlan with expanded RollbackGraph including compensation chains.
Planner never executes rollback.
"""

from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.rollback_plan import RollbackPlan, RollbackGraph, RollbackNode
from akaal.planner.analyzers.rollback_analyzer import RollbackAnalyzer


class RollbackEngine:
    """Generates RollbackPlan from risk model items."""

    def build_rollback_plan(self, ctx: PlanningContext) -> RollbackPlan:
        analyzer = RollbackAnalyzer()
        nodes = analyzer.analyze(ctx)

        rollback_graph = RollbackGraph()
        for node in nodes:
            rollback_graph.add_node(node)
        rollback_graph.ordered_rollback_ids = [n.rollback_id for n in reversed(nodes)]

        recovery_points = list({n.recovery_point_id for n in nodes if n.recovery_point_id})

        return RollbackPlan(
            strategy="FULL_COMPENSATION",
            rollback_graph=rollback_graph,
            recovery_points=recovery_points,
            rollback_validation_required=True,
        )
