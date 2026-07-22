"""
Operational Recommendation Engine.
Analyzes operational telemetry to produce explainable advisory recommendations with confidence scores.
"""

from typing import Dict, List, Any
from threading import RLock


class Recommendation:
    """An explainable operational advisory guidance item."""

    def __init__(self, rec_id: str, title: str, explanation: str, confidence_score: float, severity: str, evidence: Dict[str, Any]) -> None:
        self.rec_id = rec_id
        self.title = title
        self.explanation = explanation
        self.confidence_score = max(0.0, min(100.0, confidence_score))
        self.severity = severity  # LOW, MEDIUM, HIGH, CRITICAL
        self.evidence = evidence
        self.auto_executable = False  # Mandatory: NEVER auto-executed by Platform 9


class OperationalRecommendationEngine:
    """Generates explainable operational recommendations."""

    def __init__(self) -> None:
        self._lock = RLock()

    def analyze_telemetry(self, metrics: Dict[str, Any], health_score: float) -> List[Recommendation]:
        with self._lock:
            recs = []

            # 1. High CPU warning rule
            if metrics.get("cpu_percent", 0.0) > 85.0:
                recs.append(Recommendation(
                    rec_id="rec_cpu_scale",
                    title="Recommend Worker Scaling",
                    explanation="Host CPU utilization exceeds 85%. Scaling worker nodes will reduce thread contention.",
                    confidence_score=92.0,
                    severity="HIGH",
                    evidence={"cpu_percent": metrics.get("cpu_percent")}
                ))

            # 2. Low health score rule
            if health_score < 70.0:
                recs.append(Recommendation(
                    rec_id="rec_health_triage",
                    title="Recommend Health Triage",
                    explanation=f"Overall system health score is degraded ({health_score}/100). Check platform diagnostics.",
                    confidence_score=95.0,
                    severity="CRITICAL",
                    evidence={"health_score": health_score}
                ))

            return recs
