"""
Expanded Metrics interfaces for Enterprise Distributed Runtime (Platform 2).
Exposes metrics collection interfaces only.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from threading import RLock


class DistributedMetricsCollector(ABC):
    """Abstract DistributedMetricsCollector interface."""

    @abstractmethod
    def record_task_duration(self, task_name: str, duration_seconds: float) -> None: pass

    @abstractmethod
    def record_scheduling_throughput(self, count: int, duration_seconds: float) -> None: pass

    @abstractmethod
    def record_queue_wait_time(self, wait_seconds: float) -> None: pass

    @abstractmethod
    def record_lease_churn(self, lease_id: str, action: str) -> None: pass

    @abstractmethod
    def record_recovery_latency(self, latency_seconds: float) -> None: pass


class InMemoryDistributedMetricsCollector(DistributedMetricsCollector):
    """Thread-safe in-memory metrics collector implementation for tests and validation."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.task_durations: List[Dict[str, Any]] = []
        self.scheduling_metrics: List[Dict[str, Any]] = []
        self.queue_wait_times: List[float] = []
        self.lease_churn_events: List[Dict[str, Any]] = []
        self.recovery_latencies: List[float] = []

    def record_task_duration(self, task_name: str, duration_seconds: float) -> None:
        with self._lock:
            self.task_durations.append({"task_name": task_name, "duration": duration_seconds})

    def record_scheduling_throughput(self, count: int, duration_seconds: float) -> None:
        with self._lock:
            self.scheduling_metrics.append({"count": count, "duration": duration_seconds})

    def record_queue_wait_time(self, wait_seconds: float) -> None:
        with self._lock:
            self.queue_wait_times.append(wait_seconds)

    def record_lease_churn(self, lease_id: str, action: str) -> None:
        with self._lock:
            self.lease_churn_events.append({"lease_id": lease_id, "action": action})

    def record_recovery_latency(self, latency_seconds: float) -> None:
        with self._lock:
            self.recovery_latencies.append(latency_seconds)
