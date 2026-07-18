"""
Akaal — Complexity Engine
========================
Single-responsibility engine computing multi-dimensional MigrationComplexity scores and tiers.
"""

from typing import List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.complexity import MigrationComplexity


class ComplexityEngine:
    """Evaluates MigrationComplexity over canonical migration models."""

    def evaluate_complexity(self, ctx: RiskContext) -> MigrationComplexity:
        c_model = ctx.canonical_model
        nodes = c_model.canonical_graph.get("nodes", [])

        table_count = sum(1 for o in nodes if o.get("object_type") == "CanonicalTable")
        col_count = sum(1 for o in nodes if o.get("object_type") == "CanonicalColumn")

        structural = round(min(100.0, (table_count * 2.0) + (col_count * 0.1)), 2)
        overall = round(structural, 2)

        tier = "LOW"
        if overall > 75.0:
            tier = "CRITICAL"
        elif overall > 50.0:
            tier = "HIGH"
        elif overall > 25.0:
            tier = "MEDIUM"

        drivers = []
        if table_count > 20:
            drivers.append(f"High table count: {table_count} tables.")

        return MigrationComplexity(
            structural_complexity=structural,
            semantic_complexity=10.0,
            operational_complexity=15.0,
            performance_complexity=10.0,
            scale_complexity=round(col_count * 0.1, 2),
            overall_complexity_score=overall,
            complexity_tier=tier,
            complexity_drivers=drivers,
        )
