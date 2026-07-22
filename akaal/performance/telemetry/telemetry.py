"""
Performance Telemetry and Prometheus compatibility mapping.
"""

from typing import List, Dict, Any
from threading import RLock

from akaal.performance.event_bus.bus import PerformanceEventBus, PerformanceEvent


class TelemetryEvent(PerformanceEvent):
    """Event triggered for optimization metrics updates."""
    def __init__(self, name: str, metrics: Dict[str, Any]) -> None:
        self.name = name
        self.metrics = metrics


class PerformanceTelemetryCollector:
    """Listens to performance events to export metrics data."""

    def __init__(self, event_bus: PerformanceEventBus) -> None:
        self._lock = RLock()
        self._event_bus = event_bus
        self._metrics_log: List[Dict[str, Any]] = []

        # Subscribe to telemetry event
        self._event_bus.subscribe(TelemetryEvent, self.on_telemetry_event)

    def on_telemetry_event(self, event: TelemetryEvent) -> None:
        with self._lock:
            self._metrics_log.append({
                "metric_name": event.name,
                "values": event.metrics
            })

    def get_metrics_log(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._metrics_log)
