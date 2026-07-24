"""
AKAAL Platform 6 — Risk-Based Approval Routing Engine.
"""

from typing import Dict, Any, Tuple
from akaal.governance.domain.enums import RiskLevel


class RiskRoutingEngine:
    """Calculates risk score and determines routing track (Low-Risk Fast Track vs. High-Risk Multi-Level)."""

    def calculate_risk(self, payload: Dict[str, Any]) -> Tuple[float, RiskLevel, bool]:
        """
        Returns (risk_score, RiskLevel, is_fast_track).
        """
        base_score = 1.0

        if payload.get("is_destructive", False):
            base_score += 5.0
        if payload.get("affects_production", False):
            base_score += 3.0
        if payload.get("affects_schema", False):
            base_score += 2.0
        if payload.get("data_volume_gb", 0) > 100:
            base_score += 2.0

        risk_score = min(10.0, base_score)

        if risk_score <= 2.0:
            return risk_score, RiskLevel.LOW, True
        elif risk_score <= 5.0:
            return risk_score, RiskLevel.MEDIUM, False
        elif risk_score <= 8.0:
            return risk_score, RiskLevel.HIGH, False
        else:
            return risk_score, RiskLevel.CRITICAL, False
