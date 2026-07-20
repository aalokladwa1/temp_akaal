"""InMemoryWorkflowQueue implementation of IWorkflowQueue."""

import heapq
import threading
from typing import Dict, List, Optional
from akaal.workflow.queues.interfaces import IWorkflowQueue, StepExecutionTask


class InMemoryWorkflowQueue(IWorkflowQueue):
    """Thread-safe priority queue for local and in-memory execution."""

    def __init__(self) -> None:
        self._heap: List[tuple[int, int, StepExecutionTask]] = []  # (-priority, counter, task)
        self._tasks: Dict[str, StepExecutionTask] = {}
        self._unacked: Dict[str, StepExecutionTask] = {}
        self._dead_letter: Dict[str, tuple[StepExecutionTask, str]] = {}
        self._counter: int = 0
        self._lock = threading.Lock()

    def enqueue(self, task: StepExecutionTask) -> bool:
        with self._lock:
            self._counter += 1
            entry = (-task.priority, self._counter, task)
            heapq.heappush(self._heap, entry)
            self._tasks[task.task_id] = task
            return True

    def dequeue(self, visibility_timeout_seconds: float = 30.0) -> Optional[StepExecutionTask]:
        with self._lock:
            if not self._heap:
                return None
            _, _, task = heapq.heappop(self._heap)
            self._tasks.pop(task.task_id, None)
            self._unacked[task.task_id] = task
            return task

    def acknowledge(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._unacked:
                self._unacked.pop(task_id)
                return True
            return False

    def dead_letter(self, task_id: str, reason: str) -> bool:
        with self._lock:
            task = self._unacked.pop(task_id, None) or self._tasks.pop(task_id, None)
            if task:
                self._dead_letter[task_id] = (task, reason)
                return True
            return False

    def size(self) -> int:
        with self._lock:
            return len(self._heap)
