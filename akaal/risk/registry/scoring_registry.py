"""
Akaal — Risk Scoring Registry
=============================
Registry holding scoring thresholds and weights for Risk Platform.
"""

from typing import Dict, Any


class ScoringRegistry:
    """Scoring rules and weights repository."""

    _thresholds: Dict[str, float] = {
        "critical_severity_weight": 25.0,
        "high_severity_weight": 10.0,
        "medium_severity_weight": 3.0,
        "low_severity_weight": 1.0,
        "info_severity_weight": 0.0,
    }

    @classmethod
    def get_threshold(cls, key: str, default: float = 1.0) -> float:
        return cls._thresholds.get(key, default)
