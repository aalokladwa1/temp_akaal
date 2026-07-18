"""
Akaal — Resource Analyzer
===========================
Passive analyzer deriving resource requirements from RiskAssessmentModel.
"""

from typing import Any, Dict
from akaal.planner.models.planning_context import PlanningContext


class ResourceAnalyzer:
    analyzer_id = "resource_analyzer"

    def analyze(self, ctx: PlanningContext) -> Dict[str, Any]:
        resource_estimate = ctx.risk_model.resource_estimate
        return {
            "recommended_cpu_cores": resource_estimate.get("cpu_cores", {}).get("recommended", 4.0),
            "recommended_memory_gb": resource_estimate.get("memory_gb", {}).get("recommended", 8.0),
            "recommended_disk_gb": resource_estimate.get("disk_gb", {}).get("recommended", 50.0),
            "recommended_workers": resource_estimate.get("workers", {}).get("recommended", 4),
        }
