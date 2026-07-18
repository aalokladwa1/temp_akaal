"""
Akaal — Performance Prediction Model
====================================
Predicts migration throughput, latency, and bottleneck indicators.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PerformancePrediction:
    expected_throughput_rows_per_sec: float = 10000.0
    expected_latency_ms: float = 10.0
    confidence_score: float = 100.0
    bottleneck_indicators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_throughput_rows_per_sec": round(self.expected_throughput_rows_per_sec, 2),
            "expected_latency_ms": round(self.expected_latency_ms, 2),
            "confidence_score": round(self.confidence_score, 2),
            "bottleneck_indicators": self.bottleneck_indicators,
        }
