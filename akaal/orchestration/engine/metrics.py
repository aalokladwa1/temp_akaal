"""
MetricsCollector interface for Enterprise Orchestration Platform.
Provides extension points for recording steps, state transitions, retries, and durations.
Contains zero dashboard UI code.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from threading import RLock


class MetricsCollector(ABC):
    """Extension interface for observability metrics collection."""

    @abstractmethod
    def record_step(self, step_name: str, status: str, duration_seconds: float) -> None:
        pass

    @abstractmethod
    def record_transition(self, from_state: str, to_state: str) -> None:
        pass

    @abstractmethod
    def record_retry(self, step_name: str, count: int) -> None:
        pass

    @abstractmethod
    def record_duration(self, metric_name: str, duration_seconds: float) -> None:
        pass


class NoOpMetricsCollector(MetricsCollector):
    """No-op implementation."""
    def record_step(self, step_name: str, status: str, duration_seconds: float) -> None: pass
    def record_transition(self, from_state: str, to_state: str) -> None: pass
    def record_retry(self, step_name: str, count: int) -> None: pass
    def record_duration(self, metric_name: str, duration_seconds: float) -> None: pass


class InMemoryMetricsCollector(MetricsCollector):
    """Thread-safe in-memory metrics collector for testing and validation."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.step_metrics: List[Dict[str, Any]] = []
        self.transitions: List[Dict[str, Any]] = []
        self.retries: List[Dict[str, Any]] = []
        self.durations: List[Dict[str, Any]] = []

    def record_step(self, step_name: str, status: str, duration_seconds: float) -> None:
        with self._lock:
            self.step_metrics.append({
                "step_name": step_name,
                "status": status,
                "duration_seconds": duration_seconds,
            })

    def record_transition(self, from_state: str, to_state: str) -> None:
        with self._lock:
            self.transitions.append({
                "from_state": from_state,
                "to_state": to_state,
            })

    def record_retry(self, step_name: str, count: int) -> None:
        with self._lock:
            self.retries.append({
                "step_name": step_name,
                "count": count,
            })

    def record_duration(self, metric_name: str, duration_seconds: float) -> None:
        with self._lock:
            self.durations.append({
                "metric_name": metric_name,
                "duration_seconds": duration_seconds,
            })
