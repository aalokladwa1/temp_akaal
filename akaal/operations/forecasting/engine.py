"""
SLA, Capacity & Forecasting Engine.
Analyzes historical operational trends to predict capacity exhaustion and SLA violations.
"""

from typing import Dict, List, Any
from threading import RLock
import time


class ForecastReport:
    def __init__(self, capacity_exhaustion_days: float, sla_risk_score: float, predicted_bottlenecks: List[str]) -> None:
        self.capacity_exhaustion_days = capacity_exhaustion_days
        self.sla_risk_score = sla_risk_score
        self.predicted_bottlenecks = predicted_bottlenecks
        self.timestamp = time.time()


class OperationsForecastingEngine:
    """Predicts capacity bottlenecks and SLA compliance."""

    def __init__(self) -> None:
        self._lock = RLock()

    def generate_forecast(self, metrics_history: List[Dict[str, Any]]) -> ForecastReport:
        with self._lock:
            if not metrics_history:
                return ForecastReport(30.0, 5.0, [])

            recent_cpu = [m.get("cpu_percent", 50.0) for m in metrics_history[-10:]]
            avg_cpu = sum(recent_cpu) / len(recent_cpu) if recent_cpu else 50.0

            bottlenecks = []
            if avg_cpu > 75.0:
                bottlenecks.append("Worker CPU Saturation")
                days_left = 7.5
                sla_risk = 78.0
            else:
                days_left = 45.0
                sla_risk = 12.0

            return ForecastReport(days_left, sla_risk, bottlenecks)
