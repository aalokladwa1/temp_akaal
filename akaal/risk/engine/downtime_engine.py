"""
Akaal — Downtime Estimation Engine
==================================
Single-responsibility engine calculating cutover downtime estimates.
"""

from typing import Dict, Any, List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.downtime import DowntimeEstimate


class DowntimeEngine:
    """Estimates migration downtime based on canonical graph object counts and throughput."""

    def estimate_downtime(self, ctx: RiskContext) -> DowntimeEstimate:
        c_model = ctx.canonical_model
        objs = c_model.canonical_graph.get("nodes", [])

        # Heuristic estimation: 0.5 mins per table + base 5 mins
        table_count = sum(1 for o in objs if o.get("object_type") == "CanonicalTable")
        est_mins = round(5.0 + (table_count * 0.5), 2)

        return DowntimeEstimate(
            estimated_downtime_minutes=est_mins,
            confidence_score=95.0,
            cutover_strategy="OFFLINE_BULK",
            cdc_available=False,
            evidence=[f"Estimated downtime for {table_count} tables based on default throughput."],
        )
