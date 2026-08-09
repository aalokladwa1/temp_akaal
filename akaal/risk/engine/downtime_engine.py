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
        table_count = sum(1 for o in objs if o.get("object_type") == "CanonicalTable")

        # Prior to transport execution with measured network/disk throughput, AKAAL does not fabricate duration estimates.
        return DowntimeEstimate(
            estimated_downtime_minutes=None,
            confidence_score=0.0,
            cutover_strategy="OFFLINE_BULK",
            cdc_available=False,
            evidence=[f"Assessment pending baseline throughput measurement for {table_count} discovered objects."],
        )
