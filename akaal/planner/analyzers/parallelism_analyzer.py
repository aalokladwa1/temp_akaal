"""
Akaal — Parallelism Analyzer
==============================
Passive analyzer determining safe parallelism level from risk model and constraints.
"""

from typing import Any, Dict, List
from akaal.planner.models.planning_context import PlanningContext


class ParallelismAnalyzer:
    analyzer_id = "parallelism_analyzer"

    def analyze(self, ctx: PlanningContext) -> Dict[str, Any]:
        max_parallel = ctx.constraints.max_parallelism
        critical_count = sum(
            1 for item in ctx.risk_model.risk_items
            if item.get("severity") in ("CRITICAL", "HIGH")
        )
        # Reduce parallelism if there are critical risks
        safe_parallel = max(1, max_parallel - critical_count)

        return {
            "max_parallelism": max_parallel,
            "safe_parallelism": safe_parallel,
            "parallelism_limited_by_risk": critical_count > 0,
        }
