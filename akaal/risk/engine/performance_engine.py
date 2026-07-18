"""
Akaal — Performance Prediction Engine
====================================
Single-responsibility engine predicting migration throughput, latency, and bottleneck indicators.
"""

from typing import List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.performance_prediction import PerformancePrediction


class PerformanceEngine:
    """Predicts performance metrics over canonical migration models."""

    def predict_performance(self, ctx: RiskContext) -> PerformancePrediction:
        c_model = ctx.canonical_model
        objs = c_model.canonical_graph.get("nodes", [])

        opaque_count = sum(
            1 for o in objs if o.get("object_type") == "CanonicalColumn" and o.get("data_type", {}).get("family") == "OPAQUE"
        )

        bottlenecks = []
        if opaque_count > 0:
            bottlenecks.append(f"{opaque_count} opaque types requiring string emulation fallback.")

        return PerformancePrediction(
            expected_throughput_rows_per_sec=15000.0 if opaque_count == 0 else 8000.0,
            expected_latency_ms=12.0,
            confidence_score=90.0,
            bottleneck_indicators=bottlenecks,
        )
