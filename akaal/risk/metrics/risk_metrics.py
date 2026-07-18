"""
Akaal — Risk Metrics Collector
==============================
Operational metrics collector for Risk Platform pipeline execution.
"""

from typing import Dict, Any, Optional
from akaal.metrics.registry import MetricsRegistry


class RiskMetrics:
    """Operational metrics collector for Risk Platform."""

    def __init__(self, registry: Optional[MetricsRegistry] = None) -> None:
        self.registry = registry or MetricsRegistry()
        self.risks_detected: int = 0
        self.critical_risks: int = 0
        self.high_risks: int = 0
        self.medium_risks: int = 0
        self.low_risks: int = 0
        self.analysis_time_ms: float = 0.0

    def record_analysis_time(self, duration_ms: float) -> None:
        self.analysis_time_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risks_detected": self.risks_detected,
            "critical_risks": self.critical_risks,
            "high_risks": self.high_risks,
            "medium_risks": self.medium_risks,
            "low_risks": self.low_risks,
            "analysis_time_ms": round(self.analysis_time_ms, 2),
        }
