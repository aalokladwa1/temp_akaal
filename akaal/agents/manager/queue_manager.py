"""
NexusForge — Queue Manager
============================
Manages the six system queues as defined in TRD Section 13.

Queues:
  Discovery Queue
  Validation Queue
  Migration Queue
  Recovery Queue
  Notification Queue
  Report Queue

Each queue supports: Priority, Retry, Cancellation, Pause, Resume, Timeout.
Tasks within a queue are ordered by priority (lowest number = highest priority).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from akaal.core.models.enums import Priority, QueueName, TaskType
from akaal.core.models.task import Task, TaskStatus

logger = logging.getLogger("nexusforge.queue_manager")


# ---------------------------------------------------------------------------
# Priority Task Wrapper
# ---------------------------------------------------------------------------

@dataclass(order=True)
class PrioritizedTask:
    """Wrapper that makes Task sortable by priority for the priority queue."""
    priority_value: int         # Lower = higher priority (P0 is 0)
    insertion_order: int        # Tiebreaker — FIFO within same priority
    task: Task = field(compare=False)

    @classmethod
    def from_task(cls, task: Task, insertion_order: int) -> "PrioritizedTask":
        return cls(
            priority_value=task.priority.value,
            insertion_order=insertion_order,
            task=task,
        )


# ---------------------------------------------------------------------------
# Single Queue
# ---------------------------------------------------------------------------

class WorkQueue:
    """
    A priority-ordered, async-safe work queue with pause/resume support.

    Supports:
      - Priority ordering (P0 highest, P5 lowest)
      - FIFO within same priority
      - Pause / Resume
      - Task cancellation by ID
      - Timeout tracking
    """

    def __init__(self, name: QueueName) -> None:
        self.name = name
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._cancelled_ids: set = set()
        self._paused: bool = False
        self._insertion_counter: int = 0
        self._enqueued_count: int = 0
        self._dequeued_count: int = 0

        logger.info("[WorkQueue] Created queue: %s", name.value)

    async def enqueue(self, task: Task) -> bool:
        """
        Add a task to the queue.
        Returns False if task is already cancelled.
        """
        if task.task_id in self._cancelled_ids:
            logger.warning(
                "[WorkQueue:%s] Task %s is cancelled — not enqueued.",
                self.name.value, task.task_id
            )
            return False

        self._insertion_counter += 1
        prioritized = PrioritizedTask.from_task(task, self._insertion_counter)
        await self._queue.put(prioritized)
        self._enqueued_count += 1

        logger.debug(
            "[WorkQueue:%s] Enqueued task %s type=%s priority=%s",
            self.name.value, task.task_id[:8], task.task_type.value, task.priority.value
        )
        return True

    async def dequeue(self, timeout: float = 5.0) -> Optional[Task]:
        """
        Remove and return the next highest-priority task.
        Returns None if queue is empty or paused within timeout.
        Skips cancelled tasks automatically.
        """
        if self._paused:
            return None

        while True:
            try:
                prioritized = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                return None

            task = prioritized.task

            # Skip cancelled tasks
            if task.task_id in self._cancelled_ids:
                logger.debug(
                    "[WorkQueue:%s] Skipping cancelled task %s",
                    self.name.value, task.task_id[:8]
                )
                self._queue.task_done()
                continue

            # Skip timed-out tasks
            if task.is_timed_out():
                task.fail("Task timeout exceeded before dequeue")
                logger.warning(
                    "[WorkQueue:%s] Task %s timed out before dequeue.",
                    self.name.value, task.task_id[:8]
                )
                self._queue.task_done()
                continue

            self._dequeued_count += 1
            self._queue.task_done()
            return task

    def cancel_task(self, task_id: str) -> None:
        """Mark a task as cancelled. It will be skipped on next dequeue."""
        self._cancelled_ids.add(task_id)
        logger.info("[WorkQueue:%s] Task %s cancelled.", self.name.value, task_id[:8])

    def pause(self) -> None:
        """Pause this queue — dequeue will return None while paused."""
        self._paused = True
        logger.info("[WorkQueue:%s] Paused.", self.name.value)

    def resume(self) -> None:
        """Resume a paused queue."""
        self._paused = False
        logger.info("[WorkQueue:%s] Resumed.", self.name.value)

    def is_paused(self) -> bool:
        return self._paused

    def depth(self) -> int:
        """Current number of items in the queue."""
        return self._queue.qsize()

    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "depth": self.depth(),
            "paused": self._paused,
            "enqueued_total": self._enqueued_count,
            "dequeued_total": self._dequeued_count,
            "cancelled_ids_count": len(self._cancelled_ids),
        }


# ---------------------------------------------------------------------------
# Queue Manager
# ---------------------------------------------------------------------------

class QueueManager:
    """
    Manages all six NexusForge work queues.

    TRD Section 13: Manager shall maintain:
      Discovery Queue, Validation Queue, Migration Queue,
      Recovery Queue, Notification Queue, Report Queue.
    """

    def __init__(self) -> None:
        self._queues: Dict[QueueName, WorkQueue] = {
            q: WorkQueue(q) for q in QueueName
        }
        logger.info("[QueueManager] Initialized with %d queues.", len(self._queues))

    def get_queue(self, queue_name: QueueName) -> WorkQueue:
        return self._queues[queue_name]

    # ------------------------------------------------------------------
    # Convenience routing: task_type → queue
    # ------------------------------------------------------------------

    TASK_QUEUE_MAP: Dict[TaskType, QueueName] = {
        TaskType.DISCOVERY:          QueueName.DISCOVERY,
        TaskType.VALIDATION:         QueueName.VALIDATION,
        TaskType.GB_IMPORT:          QueueName.MIGRATION,
        TaskType.GB_VALIDATION:      QueueName.VALIDATION,
        TaskType.MIGRATION_BATCH:    QueueName.MIGRATION,
        TaskType.CDC_SYNC:           QueueName.MIGRATION,
        TaskType.CHECKPOINT_CREATE:  QueueName.MIGRATION,
        TaskType.CHECKPOINT_RESTORE: QueueName.RECOVERY,
        TaskType.HEALTH_CHECK:       QueueName.NOTIFICATION,
        TaskType.REPORT_GENERATE:    QueueName.REPORT,
        TaskType.RECOVERY:           QueueName.RECOVERY,
    }

    async def enqueue_task(self, task: Task) -> bool:
        """Route task to appropriate queue based on task type."""
        queue_name = self.TASK_QUEUE_MAP.get(task.task_type, QueueName.MIGRATION)
        return await self._queues[queue_name].enqueue(task)

    async def dequeue_discovery(self, timeout: float = 5.0) -> Optional[Task]:
        return await self._queues[QueueName.DISCOVERY].dequeue(timeout)

    async def dequeue_validation(self, timeout: float = 5.0) -> Optional[Task]:
        return await self._queues[QueueName.VALIDATION].dequeue(timeout)

    async def dequeue_migration(self, timeout: float = 5.0) -> Optional[Task]:
        return await self._queues[QueueName.MIGRATION].dequeue(timeout)

    async def dequeue_recovery(self, timeout: float = 5.0) -> Optional[Task]:
        return await self._queues[QueueName.RECOVERY].dequeue(timeout)

    def cancel_task(self, task_id: str) -> None:
        """Cancel a task across all queues."""
        for queue in self._queues.values():
            queue.cancel_task(task_id)

    def pause_all(self) -> None:
        """Pause all queues (used during system freeze)."""
        for queue in self._queues.values():
            queue.pause()
        logger.warning("[QueueManager] ALL queues paused.")

    def resume_all(self) -> None:
        """Resume all queues."""
        for queue in self._queues.values():
            queue.resume()
        logger.info("[QueueManager] ALL queues resumed.")

    def pause_queue(self, queue_name: QueueName) -> None:
        self._queues[queue_name].pause()

    def resume_queue(self, queue_name: QueueName) -> None:
        self._queues[queue_name].resume()

    def all_empty(self) -> bool:
        """Return True if all queues are empty."""
        return all(q.depth() == 0 for q in self._queues.values())

    def total_pending(self) -> int:
        """Total tasks waiting across all queues."""
        return sum(q.depth() for q in self._queues.values())

    def stats(self) -> Dict[str, Any]:
        """Return statistics for all queues."""
        return {
            q.value: self._queues[q].stats()
            for q in QueueName
        }
