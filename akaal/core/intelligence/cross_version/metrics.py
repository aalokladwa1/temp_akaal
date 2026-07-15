"""
Akaal — Cross-Version Compatibility Observability Metrics
==========================================================
Thread-safe latency counters and timing context managers for
profiling compatibility analysis runs and registry lookups.
Mirrors the compression and encryption metrics implementations.
"""

import threading
import time
from typing import Any, Dict


class CompatibilityMetricsCollector:
    """
    Thread-safe collector for profiling latency, counts, and diagnostics
    emitted during compatibility analysis runs.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "analysis_runs_total": 0,
            "registry_lookups_total": 0,
            "validation_audits_total": 0,
            "findings_generated_total": 0,
            "diagnostics_emitted_total": 0,
            "blocking_findings_total": 0,
        }
        self._latencies: Dict[str, float] = {
            "analysis_latency_sum_ms": 0.0,
            "registry_lookup_latency_sum_ms": 0.0,
            "validation_latency_sum_ms": 0.0,
        }

    def increment(self, name: str, value: int = 1) -> None:
        """Atomically increments a named counter by value."""
        with self._lock:
            if name in self._counters:
                self._counters[name] += value

    def record_latency(self, name: str, duration_ms: float) -> None:
        """Atomically accumulates a duration sample into a named latency sum."""
        with self._lock:
            if name in self._latencies:
                self._latencies[name] += duration_ms

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Returns a point-in-time copy of all counters and latency sums."""
        with self._lock:
            return {
                "counters": self._counters.copy(),
                "latencies": self._latencies.copy(),
            }


class CompatibilitySubsystemTimer:
    """
    Context manager for timing subsystem execution spans in milliseconds.

    Usage:
        with CompatibilitySubsystemTimer(collector, "analysis_latency_sum_ms"):
            ...
    """

    def __init__(
        self,
        collector: CompatibilityMetricsCollector,
        metric_name: str,
    ) -> None:
        self.collector = collector
        self.metric_name = metric_name
        self._start: float = 0.0

    def __enter__(self) -> "CompatibilitySubsystemTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000.0
        self.collector.record_latency(self.metric_name, elapsed_ms)
