"""
Akaal — Advisor Metrics Collector
==================================
Thread-safe, deterministic metrics tracking for Advisor Platform execution statistics.
"""

import threading
import time
from typing import Any, Dict


class AdvisorMetricsCollector:
    """Enterprise Thread-Safe Metrics Collector for Advisor Platform."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """Reset all metrics counters."""
        with getattr(self, "_lock", threading.Lock()):
            self._analyzer_durations_ms: Dict[str, float] = {}
            self._analyzer_success_count: int = 0
            self._analyzer_failure_count: int = 0
            self._total_recommendations: int = 0
            self._priority_distribution: Dict[str, int] = {}
            self._severity_distribution: Dict[str, int] = {}
            self._category_distribution: Dict[str, int] = {}
            self._total_processing_latency_ms: float = 0.0

    def record_analyzer_duration(self, analyzer_name: str, duration_ms: float) -> None:
        """Record execution duration of an analyzer thread-safely."""
        with self._lock:
            self._analyzer_durations_ms[analyzer_name] = float(duration_ms)

    def record_analyzer_success(self, analyzer_name: str) -> None:
        """Record successful completion of an analyzer thread-safely."""
        with self._lock:
            self._analyzer_success_count += 1

    def record_analyzer_failure(self, analyzer_name: str) -> None:
        """Record failure of an analyzer thread-safely."""
        with self._lock:
            self._analyzer_failure_count += 1

    def record_total_latency(self, latency_ms: float) -> None:
        """Record total platform processing latency in milliseconds thread-safely."""
        with self._lock:
            self._total_processing_latency_ms = float(latency_ms)

    def record_model(self, model: Any) -> None:
        """Record metrics from a produced MigrationAdvisoryModel thread-safely."""
        if hasattr(model, "recommendations"):
            recs = model.recommendations
            with self._lock:
                self._total_recommendations = len(recs)
                for rec in recs:
                    sev = rec.severity.value if hasattr(rec.severity, "value") else str(rec.severity)
                    prio = rec.priority.value if hasattr(rec.priority, "value") else str(rec.priority)
                    cat = rec.category.value if hasattr(rec.category, "value") else str(rec.category)

                    self._severity_distribution[sev] = self._severity_distribution.get(sev, 0) + 1
                    self._priority_distribution[prio] = self._priority_distribution.get(prio, 0) + 1
                    self._category_distribution[cat] = self._category_distribution.get(cat, 0) + 1

    def get_summary(self) -> Dict[str, Any]:
        """Return comprehensive metrics summary dictionary thread-safely."""
        with self._lock:
            return {
                "total_processing_latency_ms": round(self._total_processing_latency_ms, 3),
                "analyzer_durations_ms": dict(self._analyzer_durations_ms),
                "analyzer_success_count": self._analyzer_success_count,
                "analyzer_failure_count": self._analyzer_failure_count,
                "total_recommendations": self._total_recommendations,
                "priority_distribution": dict(self._priority_distribution),
                "severity_distribution": dict(self._severity_distribution),
                "category_distribution": dict(self._category_distribution),
            }
