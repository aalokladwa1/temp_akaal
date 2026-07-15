"""
Akaal — Compression Observability Metrics
=========================================
Thread-safe metrics collectors, timing trackers, and counters
for profiling compression-aware analysis runs and strategy queries.
"""

import threading
import time
from typing import Dict, Any


class CompressionMetricsCollector:
    """Thread-safe collector for profiling latency, counts, cache performance, and diagnostics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "analysis_runs_total": 0,
            "registry_lookups_total": 0,
            "validation_audits_total": 0,
            "recommendations_generated_total": 0,
            "diagnostics_emitted_total": 0
        }
        self._latencies: Dict[str, float] = {
            "analysis_latency_sum_ms": 0.0,
            "registry_lookup_latency_sum_ms": 0.0,
            "validation_latency_sum_ms": 0.0
        }

    def increment(self, name: str, value: int = 1) -> None:
        """Atomically increments a counter metric."""
        with self._lock:
            if name in self._counters:
                self._counters[name] += value

    def record_latency(self, name: str, duration_ms: float) -> None:
        """Atomically appends execution duration to latency sums."""
        with self._lock:
            if name in self._latencies:
                self._latencies[name] += duration_ms

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Returns a snapshot copy of current counters and timings."""
        with self._lock:
            return {
                "counters": self._counters.copy(),
                "latencies": self._latencies.copy()
            }


class SubsystemTimer:
    """Context manager for tracking elapsed execution times in milliseconds."""

    def __init__(self, collector: CompressionMetricsCollector, metric_name: str) -> None:
        self.collector = collector
        self.metric_name = metric_name
        self.start_time: float = 0.0

    def __enter__(self) -> "SubsystemTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0
        self.collector.record_latency(self.metric_name, elapsed_ms)
