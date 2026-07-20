"""Dead Letter Queue and Replay Manager."""

import threading
from typing import Dict, List, Optional, Tuple
from akaal.workflow.queues.interfaces import StepExecutionTask
from akaal.workflow.utils.clock import IClock, SystemClock


class DeadLetterQueue:
    """Thread-safe Dead Letter Queue managing poison tasks and replay."""

    def __init__(self, clock: IClock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._dlq: Dict[str, Tuple[StepExecutionTask, str, str]] = {}  # task_id -> (task, reason, timestamp)
        self._lock = threading.Lock()

    def add_poison_task(self, task: StepExecutionTask, reason: str) -> None:
        with self._lock:
            self._dlq[task.task_id] = (task, reason, self._clock.now_utc())

    def get_poison_task(self, task_id: str) -> Optional[Tuple[StepExecutionTask, str, str]]:
        with self._lock:
            return self._dlq.get(task_id)

    def list_poison_tasks(self) -> List[Tuple[StepExecutionTask, str, str]]:
        with self._lock:
            return list(self._dlq.values())

    def replay_task(self, task_id: str) -> Optional[StepExecutionTask]:
        """Reclaim task from dead letter queue for replay."""
        with self._lock:
            entry = self._dlq.pop(task_id, None)
            if entry:
                return entry[0]
            return None
