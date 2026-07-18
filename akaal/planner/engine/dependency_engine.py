"""
Akaal — Dependency Engine
==========================
Builds PlannerDependencyGraph with dependency semantics, cycle detection, and topological ordering.
"""

from typing import Any, Dict, List, Set
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.execution_graph import ExecutionGraph
from akaal.planner.models.dependency_graph import PlannerDependencyGraph
from akaal.planner.models.planning_decision import PlanningDecision


class DependencyEngine:
    """Analyzes ExecutionGraph for dependency chains, cycles, and independent groups."""

    def build_dependency_graph(
        self, ctx: PlanningContext, graph: ExecutionGraph
    ) -> PlannerDependencyGraph:
        dep_graph = PlannerDependencyGraph()

        # Find nodes with no predecessors (roots)
        has_incoming: Set[str] = set()
        for src, targets in graph.edges.items():
            for t in targets:
                has_incoming.add(t)

        independent_roots = [t_id for t_id in graph.tasks if t_id not in has_incoming]
        dep_graph.independent_groups = [independent_roots] if independent_roots else []

        # Topological sort gives critical chain
        sorted_tasks = graph.topological_sort()
        dep_graph.critical_chain = [t.task_id for t in sorted_tasks]

        # Blocking = tasks with CRITICAL severity risk references
        risk_items = ctx.risk_model.risk_items
        critical_risks = {item.get("risk_id") for item in risk_items if item.get("severity") == "CRITICAL"}
        dep_graph.blocking_operations = [
            t.task_id for t in sorted_tasks
            if any(r in t.target_object_id for r in critical_risks)
        ]

        return dep_graph
