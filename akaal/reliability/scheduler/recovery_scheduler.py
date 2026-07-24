"""Reliability Retry, Recovery, and Maintenance Schedulers."""

import time
import heapq
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass(order=True)
class ScheduledReliabilityTask:
    priority: int
    scheduled_time: float
    task_id: str = field(compare=False)
    task_type: str = field(compare=False)
    payload: Dict[str, Any] = field(compare=False)


class ReliabilityRetryScheduler:
    """Schedules retries with exponential backoff and SLA awareness."""

    def calculate_backoff_delay(self, attempt: int, base_delay_sec: float = 1.0, max_delay_sec: float = 30.0) -> float:
        delay = base_delay_sec * (2 ** (attempt - 1))
        return min(delay, max_delay_sec)

    def schedule_retry(self, task_id: str, attempt: int, payload: Dict[str, Any]) -> ScheduledReliabilityTask:
        delay = self.calculate_backoff_delay(attempt)
        scheduled_at = time.time() + delay
        priority = max(1, 10 - attempt)
        return ScheduledReliabilityTask(priority, scheduled_at, task_id, "RETRY", payload)


class ReliabilityRecoveryScheduler:
    """Manages prioritized recovery queues for failed components."""

    def __init__(self):
        self._queue: List[ScheduledReliabilityTask] = []
        self._lock = threading.RLock()

    def enqueue_recovery(self, component_name: str, priority: int = 1, payload: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            task = ScheduledReliabilityTask(priority, time.time(), component_name, "RECOVERY", payload or {})
            heapq.heappush(self._queue, task)

    def pop_next_recovery(self) -> Optional[ScheduledReliabilityTask]:
        with self._lock:
            if self._queue:
                return heapq.heappop(self._queue)
            return None


class MaintenanceWindowScheduler:
    """Coordinates planned maintenance windows and deferred recovery tasks."""

    def __init__(self):
        self.in_maintenance = False

    def set_maintenance_mode(self, active: bool) -> None:
        self.in_maintenance = active

    def is_maintenance_active(self) -> bool:
        return self.in_maintenance
