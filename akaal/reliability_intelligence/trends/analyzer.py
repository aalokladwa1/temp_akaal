"""
AKAAL Platform 9 — Reliability Trend Analyzer.
"""

from typing import List, Dict, Any


class ReliabilityTrendAnalyzer:
    """Analyzes historical reliability trends over extended windows."""

    def analyze_trends(self, metric_samples: List[float]) -> Dict[str, Any]:
        if not metric_samples:
            return {"mean": 0.0, "trend_direction": "STABLE"}

        mean_val = sum(metric_samples) / len(metric_samples)
        is_increasing = metric_samples[-1] > metric_samples[0]
        direction = "DEGRADED" if is_increasing else "IMPROVING"

        return {
            "mean_sample_val": round(mean_val, 2),
            "trend_direction": direction,
            "sample_count": len(metric_samples),
        }
