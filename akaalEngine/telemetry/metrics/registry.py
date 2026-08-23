"""
akaalEngine.telemetry.metrics.registry
=======================================
High-performance thread-safe MetricsRegistry managing Counters, Gauges, Histograms, and RateTimers.
Mined from `akaal/distributed/metrics/` and `akaal/performance/telemetry/`.
"""

from collections import deque
import logging
import math
from threading import RLock
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

from akaalEngine.telemetry.metrics.cardinality import CardinalityGuard
from akaalEngine.telemetry.models.errors import InvalidMetricValueError
from akaalEngine.telemetry.models.metric import (
    MetricDescriptor,
    MetricSnapshot,
    MetricType,
    MetricValue,
)

logger = logging.getLogger("akaalEngine.telemetry.metrics.registry")


class MetricsRegistry:
    """
    Thread-safe MetricsRegistry supporting Counters, Gauges, Histograms (with real P50/P95/P99 percentiles),
    and RateTimers. Enforces cardinality bounds.
    """

    def __init__(self, cardinality_guard: Optional[CardinalityGuard] = None) -> None:
        self.guard = cardinality_guard or CardinalityGuard()
        self._descriptors: Dict[str, MetricDescriptor] = {}
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._gauges: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], deque[float]] = {}
        self._rate_timers: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Tuple[float, int]] = {}  # sum, count
        self._lock = RLock()

    def register_descriptor(self, descriptor: MetricDescriptor) -> None:
        with self._lock:
            self._descriptors[descriptor.name] = descriptor

    def _make_key(self, name: str, labels: Optional[Mapping[str, str]]) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        safe_labels = self.guard.check_and_register(name, labels or {})
        return name, tuple(sorted(safe_labels.items()))

    # --- Counter ---
    def record_counter(self, name: str, increment: float = 1.0, labels: Optional[Mapping[str, str]] = None) -> None:
        if increment < 0:
            raise InvalidMetricValueError(name, increment, "Counter increments must be non-negative.")
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] = self._counters.get(key, 0.0) + increment

    # --- Gauge ---
    def set_gauge(self, name: str, value: float, labels: Optional[Mapping[str, str]] = None) -> None:
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = float(value)

    # --- Histogram ---
    def observe_histogram(self, name: str, value: float, labels: Optional[Mapping[str, str]] = None, max_samples: int = 500) -> None:
        with self._lock:
            key = self._make_key(name, labels)
            dq = self._histograms.setdefault(key, deque(maxlen=max_samples))
            dq.append(float(value))

    # --- Rate / Timer ---
    def observe_timer(self, name: str, duration_seconds: float, labels: Optional[Mapping[str, str]] = None) -> None:
        if duration_seconds < 0:
            raise InvalidMetricValueError(name, duration_seconds, "Timer duration must be non-negative.")
        with self._lock:
            key = self._make_key(name, labels)
            curr_sum, curr_count = self._rate_timers.get(key, (0.0, 0))
            self._rate_timers[key] = (curr_sum + duration_seconds, curr_count + 1)

    # --- Calculations ---
    @staticmethod
    def _calculate_percentile(data: List[float], percentile: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return round(sorted_data[int(k)], 4)
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return round(d0 + d1, 4)

    def get_snapshot(self) -> MetricSnapshot:
        with self._lock:
            now = time.time()
            c_out: Dict[str, float] = {}
            for (m_name, label_tuple), val in self._counters.items():
                lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple) if label_tuple else ""
                key_name = f"{m_name}{{{lbl_str}}}" if lbl_str else m_name
                c_out[key_name] = val

            g_out: Dict[str, float] = {}
            for (m_name, label_tuple), val in self._gauges.items():
                lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple) if label_tuple else ""
                key_name = f"{m_name}{{{lbl_str}}}" if lbl_str else m_name
                g_out[key_name] = val

            h_out: Dict[str, Dict[str, float]] = {}
            for (m_name, label_tuple), samples in self._histograms.items():
                s_list = list(samples)
                lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple) if label_tuple else ""
                key_name = f"{m_name}{{{lbl_str}}}" if lbl_str else m_name
                h_out[key_name] = {
                    "count": float(len(s_list)),
                    "sum": round(sum(s_list), 4),
                    "p50": self._calculate_percentile(s_list, 50.0),
                    "p95": self._calculate_percentile(s_list, 95.0),
                    "p99": self._calculate_percentile(s_list, 99.0),
                }

            t_out: Dict[str, Dict[str, float]] = {}
            for (m_name, label_tuple), (total_sum, count) in self._rate_timers.items():
                lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple) if label_tuple else ""
                key_name = f"{m_name}{{{lbl_str}}}" if lbl_str else m_name
                avg = round(total_sum / float(count), 4) if count > 0 else 0.0
                t_out[key_name] = {
                    "count": float(count),
                    "total_seconds": round(total_sum, 4),
                    "avg_seconds": avg,
                }

            return MetricSnapshot(
                timestamp=now,
                counters=c_out,
                gauges=g_out,
                histograms=h_out,
                rate_timers=t_out,
            )
