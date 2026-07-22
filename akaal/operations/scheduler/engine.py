"""
Enterprise Operations Scheduler.
Schedules and executes internal operational housekeeping tasks.
"""

from typing import Dict, List, Callable, Any, Optional
from threading import RLock
import time


class ScheduledTask:
    def __init__(self, task_id: str, name: str, interval_seconds: float, handler: Callable[[], None]) -> None:
        self.task_id = task_id
        self.name = name
        self.interval_seconds = interval_seconds
        self.handler = handler
        self.last_run: float = 0.0
        self.run_count: int = 0
        self.failure_count: int = 0


class OperationsScheduler:
    """Internal task scheduler for operational tasks."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._tasks: Dict[str, ScheduledTask] = {}

    def schedule_task(self, name: str, interval_seconds: float, handler: Callable[[], None]) -> str:
        with self._lock:
            tid = f"task_{time.time_ns()}_{len(self._tasks)}"
            task = ScheduledTask(tid, name, interval_seconds, handler)
            self._tasks[tid] = task
            return tid

    def trigger_due_tasks(self) -> List[str]:
        return self.run_pending()
    
    def run_pending(self) -> List[str]:
        with self._lock:
            now = time.time()
            executed = []
            for task in self._tasks.values():
                if now - task.last_run >= task.interval_seconds:
                    try:
                        task.handler()
                        task.last_run = now
                        task.run_count += 1
                        executed.append(task.name)
                    except Exception:
                        task.failure_count += 1
            return executed
