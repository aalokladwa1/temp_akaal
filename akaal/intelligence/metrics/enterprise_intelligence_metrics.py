"""
AKAAL Enterprise Intelligence Platform — Metrics Subsystem
===========================================================
Thread-safe microsecond execution timing and event counters collector for Platform 2.
"""

import threading
import time
from typing import Any, Dict


class EnterpriseIntelligenceMetricsCollector:
    """
    Thread-safe metrics collector capturing execution durations and event counters.
    """

    def __init__(self) -> None:
        self._durations_ms: Dict[str, float] = {}
        self._counters: Dict[str, int] = {}
        self._success_count: int = 0
        self._failure_count: int = 0
        self._lock: threading.Lock = threading.Lock()

    def record_duration(self, metric_name: str, duration_ms: float) -> None:
        """Records an execution duration in milliseconds."""
        with self._lock:
            self._durations_ms[metric_name] = max(0.0, float(duration_ms))

    def increment_counter(self, counter_name: str, amount: int = 1) -> None:
        """Increments a telemetry counter."""
        with self._lock:
            self._counters[counter_name] = self._counters.get(counter_name, 0) + int(amount)

    def record_success(self) -> None:
        """Increments success execution counter."""
        with self._lock:
            self._success_count += 1

    def record_failure(self) -> None:
        """Increments failure execution counter."""
        with self._lock:
            self._failure_count += 1

    def get_snapshot(self) -> Dict[str, Any]:
        """Returns an immutable dictionary snapshot of current metrics."""
        with self._lock:
            return {
                "durations_ms": dict(self._durations_ms),
                "counters": dict(self._counters),
                "success_count": self._success_count,
                "failure_count": self._failure_count,
            }

    def reset(self) -> None:
        """Resets all metrics and counters."""
        with self._lock:
            self._durations_ms.clear()
            self._counters.clear()
            self._success_count = 0
            self._failure_count = 0


class TimerContext:
    """Context manager for timing pipeline code blocks."""

    def __init__(self, collector: EnterpriseIntelligenceMetricsCollector, metric_name: str) -> None:
        self._collector = collector
        self._metric_name = metric_name
        self._start_time: float = 0.0

    def __enter__(self) -> "TimerContext":
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000.0
        self._collector.record_duration(self._metric_name, elapsed_ms)
        if exc_type is not None:
            self._collector.record_failure()
