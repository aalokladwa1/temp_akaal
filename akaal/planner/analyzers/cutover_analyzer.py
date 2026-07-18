"""
Akaal — Cutover Analyzer
==========================
Passive analyzer determining cutover window strategy from readiness model.
"""

from typing import Any, Dict
from akaal.planner.models.planning_context import PlanningContext
from akaal.planner.models.cutover_plan import CutoverPhaseType


class CutoverAnalyzer:
    analyzer_id = "cutover_analyzer"

    def analyze(self, ctx: PlanningContext) -> Dict[str, Any]:
        readiness = ctx.risk_model.readiness
        classification = readiness.get("classification", "READY")

        return {
            "recommended_strategy": "BULK_CUTOVER",
            "readiness_classification": classification,
            "rollback_window_minutes": 30.0 if classification == "READY" else 60.0,
            "validation_required": True,
        }
