"""ObservabilityService: Repair telemetry, MTTR, latency, success/failure rate, queue size."""

import time
import threading
from typing import Dict, Any
from akaal.healing.core.interfaces import IHealingService


class ObservabilityService(IHealingService):
    """Infrastructure service collecting healing performance and telemetry metrics."""

    @property
    def service_name(self) -> str:
        return "ObservabilityService"

    def __init__(self):
        self._lock = threading.RLock()
        self._metrics: Dict[str, Any] = {
            "total_repairs": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "rollbacks_executed": 0,
            "total_repair_time_seconds": 0.0,
            "mttr_seconds": 0.0,
        }

    def record_repair_result(self, success: bool, duration_seconds: float) -> None:
        """Record repair metrics."""
        with self._lock:
            self._metrics["total_repairs"] += 1
            if success:
                self._metrics["successful_repairs"] += 1
            else:
                self._metrics["failed_repairs"] += 1

            self._metrics["total_repair_time_seconds"] += duration_seconds
            total = self._metrics["total_repairs"]
            self._metrics["mttr_seconds"] = self._metrics["total_repair_time_seconds"] / total if total > 0 else 0.0

    def get_telemetry(self) -> Dict[str, Any]:
        """Return current telemetry snapshot."""
        with self._lock:
            return dict(self._metrics)
