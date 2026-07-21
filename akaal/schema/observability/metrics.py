"""
AKAAL Platform 5 — Prometheus-Compatible Metrics Collector

Collects execution counters, latency distributions, cache ratios, and transaction stats.
"""

from collections import defaultdict
import threading
from typing import Dict, Any


class SchemaMetricsCollector:
    """Thread-safe telemetry metrics collector."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, list] = defaultdict(list)

    def increment_counter(self, metric_name: str, value: int = 1, labels: str = "") -> None:
        key = f"{metric_name}{{{labels}}}" if labels else metric_name
        with self._lock:
            self._counters[key] += value

    def observe_duration(self, metric_name: str, duration_seconds: float, labels: str = "") -> None:
        key = f"{metric_name}{{{labels}}}" if labels else metric_name
        with self._lock:
            self._histograms[key].append(duration_seconds)

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            histogram_stats = {}
            for k, v in self._histograms.items():
                if v:
                    histogram_stats[k] = {
                        "count": len(v),
                        "total_seconds": sum(v),
                        "avg_seconds": sum(v) / len(v),
                        "max_seconds": max(v),
                    }
            return {
                "counters": dict(self._counters),
                "histograms": histogram_stats,
            }
