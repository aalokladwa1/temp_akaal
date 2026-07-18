"""
Akaal — Rollback Analyzer
===========================
Passive analyzer generating rollback nodes from risk items and stage ordering.
"""

from typing import List
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.rollback_plan import RollbackNode


class RollbackAnalyzer:
    analyzer_id = "rollback_analyzer"

    def analyze(self, ctx: PlanningContext) -> List[RollbackNode]:
        nodes = []
        for i, risk_item in enumerate(ctx.risk_model.risk_items):
            node = RollbackNode(
                rollback_id=f"ROLLBACK-{i+1}",
                task_id=f"task_{risk_item.get('risk_id', f'r{i}')}",
                compensation_action="REVERSE_OPERATION",
                recovery_point_id=f"CHKPT-STAGE-1",
            )
            nodes.append(node)
        return nodes
