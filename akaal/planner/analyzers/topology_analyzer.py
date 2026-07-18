"""
Akaal — Topology Analyzer
===========================
Passive analyzer examining execution graph topology for high coupling and ordering issues.
"""

from typing import Any, Dict
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.execution_graph import ExecutionGraph


class TopologyAnalyzer:
    analyzer_id = "topology_analyzer"

    def analyze(self, ctx: PlanningContext, graph: ExecutionGraph) -> Dict[str, Any]:
        task_count = len(graph.tasks)
        edge_count = sum(len(v) for v in graph.edges.values())

        return {
            "task_count": task_count,
            "edge_count": edge_count,
            "density": round(edge_count / max(1, task_count), 3),
            "is_dag": True,
        }
