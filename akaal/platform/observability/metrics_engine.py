"""
Metrics Engine & High-Cardinality Metrics Registry (Prometheus & OpenTelemetry Compatible).
"""

from dataclasses import dataclass, field
import threading
import time
from typing import Dict, List, Optional


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp_ms: int
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsRegistry:
    """Thread-safe metric registry storing counters, gauges, and histograms."""

    def __init__(self) -> None:
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def increment_counter(self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> float:
        key = self._format_key(name, labels)
        with self._lock:
            val = self._counters.get(key, 0.0) + amount
            self._counters[key] = val
            return val

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> float:
        key = self._format_key(name, labels)
        with self._lock:
            self._gauges[key] = value
            return value

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._format_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        key = self._format_key(name, labels)
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        key = self._format_key(name, labels)
        with self._lock:
            return self._gauges.get(key, 0.0)

    def _format_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class MetricsEngine:
    """Aggregates metrics and exports Prometheus-compatible exposition format."""

    def __init__(self, registry: MetricsRegistry) -> None:
        self.registry = registry

    def export_prometheus_format(self) -> str:
        lines = []
        with self.registry._lock:
            for k, v in self.registry._counters.items():
                lines.append(f"# TYPE {k.split('{')[0]} counter")
                lines.append(f"{k} {v}")
            for k, v in self.registry._gauges.items():
                lines.append(f"# TYPE {k.split('{')[0]} gauge")
                lines.append(f"{k} {v}")
        return "\n".join(lines)
