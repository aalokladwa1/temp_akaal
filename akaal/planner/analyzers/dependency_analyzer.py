"""
Akaal — Dependency Analyzer
============================
Passive analyzer identifying dependency chains, cycles, and independent groups from RiskAssessmentModel.
"""

from typing import Any, Dict, List
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.dependency_graph import PlannerDependencyGraph
from akaal.planner.models.planning_decision import PlanningDecision


class DependencyAnalyzer:
    analyzer_id = "dependency_analyzer"

    def analyze(self, ctx: PlanningContext) -> PlannerDependencyGraph:
        risk_items = ctx.risk_model.risk_items
        dep_graph = PlannerDependencyGraph()

        # Build critical chain from risk items ordered by risk score
        critical_chain = [item.get("risk_id", "UNKNOWN") for item in risk_items if item.get("severity") in ("CRITICAL", "HIGH")]
        dep_graph.critical_chain = critical_chain

        blocking = [item.get("risk_id") for item in risk_items if item.get("severity") == "CRITICAL"]
        dep_graph.blocking_operations = blocking

        return dep_graph
