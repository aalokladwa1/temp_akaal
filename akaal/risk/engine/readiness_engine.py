"""
Akaal — Readiness Engine
========================
Single-responsibility engine computing multi-dimensional CutoverReadiness.
"""

from typing import List
from akaal.risk.models.risk_context import RiskContext
from akaal.risk.models.risk_item import RiskItem
from akaal.risk.models.readiness import CutoverReadiness, ReadinessClassification


class ReadinessEngine:
    """Evaluates CutoverReadiness status."""

    def evaluate_readiness(self, ctx: RiskContext, risk_items: List[RiskItem]) -> CutoverReadiness:
        critical_count = sum(1 for r in risk_items if r.severity == "CRITICAL")
        high_count = sum(1 for r in risk_items if r.severity == "HIGH")

        blockers = [r.root_cause for r in risk_items if r.severity == "CRITICAL"]

        if critical_count > 0:
            classification = ReadinessClassification.NOT_READY
        elif high_count > 0:
            classification = ReadinessClassification.HIGH_RISK
        elif len(risk_items) > 0:
            classification = ReadinessClassification.READY_WITH_WARNINGS
        else:
            classification = ReadinessClassification.READY

        return CutoverReadiness(
            technical_readiness=round(max(0.0, 100.0 - (critical_count * 30.0 + high_count * 15.0)), 2),
            operational_readiness=90.0,
            infrastructure_readiness=95.0,
            data_readiness=round(max(0.0, 100.0 - (critical_count * 20.0)), 2),
            classification=classification,
            blockers=blockers,
        )
