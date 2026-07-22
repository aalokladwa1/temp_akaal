"""
Unified Observability Platform Collector.
Consumes OpenTelemetry traces, Prometheus metrics, logs, and events across platforms.
"""

from typing import Dict, List, Any
from threading import RLock
import time


class ObservabilityCollector:
    """Aggregates telemetry without duplicating metric generator logic."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._metrics: List[Dict[str, Any]] = []
        self._logs: List[Dict[str, Any]] = []
        self._traces: List[Dict[str, Any]] = []

    def ingest_metric(self, name: str, value: float, labels: Dict[str, str]) -> None:
        with self._lock:
            self._metrics.append({
                "timestamp": time.time(),
                "name": name,
                "value": value,
                "labels": labels
            })

    def ingest_log(self, level: str, message: str, correlation_id: str, source_platform: str) -> None:
        with self._lock:
            self._logs.append({
                "timestamp": time.time(),
                "level": level,
                "message": message,
                "correlation_id": correlation_id,
                "source_platform": source_platform
            })

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_metrics": len(self._metrics),
                "total_logs": len(self._logs),
                "total_traces": len(self._traces)
            }
