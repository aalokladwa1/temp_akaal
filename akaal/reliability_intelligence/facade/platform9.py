"""
AKAAL Platform 9 — Reliability Intelligence Main Engine (ReliabilityIntelligencePlatformV9).
"""

from typing import Dict, Any, List
from akaal.reliability_intelligence.regression.engine import ReliabilityRegressionEngine
from akaal.reliability_intelligence.baseline.comparator import ReliabilityBaselineComparator
from akaal.reliability_intelligence.trends.analyzer import ReliabilityTrendAnalyzer
from akaal.reliability_intelligence.drift.detector import ReliabilityDriftDetector
from akaal.reliability_intelligence.recommendations.engine import ReliabilityRecommendationEngine
from akaal.reliability_intelligence.domain.models import (
    DriftReport,
    RegressionReport,
    ReliabilityBaseline,
    ReliabilityRecommendation,
)


class ReliabilityIntelligencePlatformV9:
    """
    Centralized Reliability Intelligence Platform (AKAAL Phase 13 Platform 9).
    Continuously evaluates reliability quality, baseline comparisons, drift detection, and automated recommendations.
    """

    def __init__(self) -> None:
        self.platform_name = "Phase 13 Platform 9 — Reliability Intelligence Platform"
        self.version = "9.0.0"
        self.profile = "ENTERPRISE"

        self.regression_engine = ReliabilityRegressionEngine()
        self.baseline_comparator = ReliabilityBaselineComparator()
        self.trend_analyzer = ReliabilityTrendAnalyzer()
        self.drift_detector = ReliabilityDriftDetector()
        self.recommendation_engine = ReliabilityRecommendationEngine()

    def evaluate_regression(self, target_name: str, baseline_p99_ms: float, current_p99_ms: float) -> RegressionReport:
        return self.regression_engine.evaluate_regression(target_name, baseline_p99_ms, current_p99_ms)

    def create_baseline(self, target_name: str, p99_latency_ms: float, error_rate_pct: float, availability_pct: float) -> ReliabilityBaseline:
        return self.baseline_comparator.create_baseline(target_name, p99_latency_ms, error_rate_pct, availability_pct)

    def analyze_trends(self, metric_samples: List[float]) -> Dict[str, Any]:
        return self.trend_analyzer.analyze_trends(metric_samples)

    def detect_drift(self, target_name: str, baseline_p99_ms: float, current_p99_ms: float) -> DriftReport:
        return self.drift_detector.detect_drift(target_name, baseline_p99_ms, current_p99_ms)

    def generate_recommendation(self, service_id: str, title: str, action_item: str) -> ReliabilityRecommendation:
        return self.recommendation_engine.generate_recommendation(service_id, title, action_item)
