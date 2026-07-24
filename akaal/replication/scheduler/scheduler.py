"""ReplicationScheduler: Priority Queue and SLA-aware scheduling engine."""

import heapq
import threading
from typing import Any, List, Optional, Tuple


class PriorityQueue:
    """Min-heap priority queue for replication tasks."""

    def __init__(self):
        self._heap: List[Tuple[int, str, Any]] = []
        self._lock = threading.RLock()

    def push(self, task_id: str, item: Any, priority: int) -> None:
        with self._lock:
            # Lower numerical priority value = higher priority execution
            heapq.heappush(self._heap, (-priority, task_id, item))

    def pop(self) -> Optional[Any]:
        with self._lock:
            if self._heap:
                return heapq.heappop(self._heap)[2]
            return None


class SLAEngine:
    """Calculates priority scores based on business criticality and SLA deadlines."""

    def calculate_priority(self, criticality: str) -> int:
        if criticality == "CRITICAL":
            return 100
        elif criticality == "HIGH":
            return 75
        return 50


class ReplicationScheduler:
    """Schedules and prioritizes replication workloads."""

    def __init__(self):
        self.queue = PriorityQueue()
        self.sla_engine = SLAEngine()

    def schedule_replication(self, task_id: str, plan: Any, criticality: str = "MEDIUM") -> None:
        score = self.sla_engine.calculate_priority(criticality)
        self.queue.push(task_id, plan, score)

    def get_next_task(self) -> Optional[Any]:
        return self.queue.pop()
