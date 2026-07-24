"""ObservabilityService: Real-time telemetry, performance metrics, and progress reporting."""

import time
import threading
from typing import Any, Dict
from akaal.validation.core.interfaces import IService


class ObservabilityService(IService):
    """Infrastructure service collecting real-time metrics, throughput, latency, and resource utilization."""

    @property
    def service_name(self) -> str:
        return "ObservabilityService"

    def __init__(self):
        self._lock = threading.RLock()
        self._metrics: Dict[str, Any] = {
            "total_rows_validated": 0,
            "total_issues_detected": 0,
            "start_time": time.time(),
            "domain_latencies_ms": {},
            "active_workers": 0,
        }

    def record_rows(self, count: int) -> None:
        """Add to total validated rows counter."""
        with self._lock:
            self._metrics["total_rows_validated"] += count

    def record_issues(self, count: int) -> None:
        """Add to total detected issues counter."""
        with self._lock:
            self._metrics["total_issues_detected"] += count

    def record_latency(self, domain_name: str, latency_ms: float) -> None:
        """Record domain validator execution latency."""
        with self._lock:
            self._metrics["domain_latencies_ms"][domain_name] = latency_ms

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Return snapshot of current validation telemetry."""
        with self._lock:
            elapsed = time.time() - self._metrics["start_time"]
            rows = self._metrics["total_rows_validated"]
            throughput = rows / elapsed if elapsed > 0 else 0.0
            return {
                "total_rows_validated": rows,
                "total_issues_detected": self._metrics["total_issues_detected"],
                "elapsed_seconds": round(elapsed, 3),
                "throughput_rows_per_sec": round(throughput, 2),
                "domain_latencies_ms": dict(self._metrics["domain_latencies_ms"]),
            }
