"""
Confidence Scoring Engine for Decision Layer.
Generates metrics for rule engine suggestions.
"""

from typing import Dict, Any
from enum import Enum


class ConfidenceCategory(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class OptimizationConfidence:
    """Represents a calculated confidence rating for a recommended optimization."""
    def __init__(
        self,
        score: float,
        reason: str,
        expected_improvement: float,
        expected_risk: float,
        category: ConfidenceCategory
    ) -> None:
        self.score = score
        self.reason = reason
        self.expected_improvement = expected_improvement
        self.expected_risk = expected_risk
        self.category = category

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "reason": self.reason,
            "expected_improvement": self.expected_improvement,
            "expected_risk": self.expected_risk,
            "category": self.category.value,
        }


class ConfidenceEngine:
    """Calculates risk, benefits, and categories for suggested changes."""

    @staticmethod
    def calculate(metric_delta: float, success_history: float, risk_factor: float) -> OptimizationConfidence:
        # Simple deterministic formula based on historical success rates and delta
        raw_score = (success_history * 0.7) + ((1.0 - risk_factor) * 0.3)
        score = min(max(raw_score, 0.0), 1.0)

        if score >= 0.85:
            category = ConfidenceCategory.HIGH
        elif score >= 0.50:
            category = ConfidenceCategory.MEDIUM
        else:
            category = ConfidenceCategory.LOW

        expected_imp = metric_delta * score
        expected_rk = risk_factor * (1.0 - score)

        return OptimizationConfidence(
            score=round(score * 100.0, 2),
            reason="Based on execution latency history and minimal system impact constraints.",
            expected_improvement=round(expected_imp * 100.0, 2),
            expected_risk=round(expected_rk * 100.0, 2),
            category=category
        )
