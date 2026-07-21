"""
Transport-Agnostic Task Queue with Idempotency & Priority Support.
Supports Priority, Delayed, and Retry queues with IdempotencyKey deduplication.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import RLock
from typing import Optional, List, Dict, Any
import heapq

from akaal.distributed.domain.identifiers import TaskId, IdempotencyKey, ExecutionId
from akaal.distributed.domain.models import Task, ExecutionRequest
from akaal.distributed.domain.errors import TaskDistributionError
from akaal.distributed.clock.clock import Clock, SystemClock


class TaskQueue(ABC):
    """Transport-agnostic TaskQueue interface."""

    @abstractmethod
    def enqueue(self, request: ExecutionRequest) -> bool:
        """Enqueue an execution request. Returns True if queued, False if deduplicated via IdempotencyKey."""
        pass

    @abstractmethod
    def dequeue(self) -> Optional[ExecutionRequest]:
        """Dequeue the highest-priority ready execution request."""
        pass

    @abstractmethod
    def requeue_for_retry(self, request: ExecutionRequest, delay_seconds: float = 0.0) -> None:
        """Requeue a task execution for retry."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Return count of queued tasks."""
        pass

    @abstractmethod
    def get_by_idempotency_key(self, key: IdempotencyKey) -> Optional[ExecutionRequest]:
        """Retrieve execution request by idempotency key."""
        pass


class MemoryTaskQueue(TaskQueue):
    """
    Thread-safe MemoryTaskQueue supporting Priority, Delayed, and Retry queues
    with IdempotencyKey deduplication using a injected Clock.
    """

    def __init__(self, clock: Optional[Clock] = None) -> None:
        self._lock = RLock()
        self._clock = clock or SystemClock()
        self._idempotency_map: Dict[str, ExecutionRequest] = {}
        
        # Priority heap entries: (-priority, available_timestamp, sequence, ExecutionRequest)
        self._queue: List[Tuple[int, float, int, ExecutionRequest]] = []
        self._sequence = 0

    def enqueue(self, request: ExecutionRequest) -> bool:
        with self._lock:
            key_str = str(request.idempotency_key)
            if key_str in self._idempotency_map:
                # Deduplicated!
                return False

            self._idempotency_map[key_str] = request
            self._sequence += 1
            
            avail_time = self._clock.now_timestamp() + request.task.delay_seconds
            # Lower value for priority means higher priority in standard min-heap, so negate priority
            heapq.heappush(self._queue, (-request.task.priority, avail_time, self._sequence, request))
            return True

    def dequeue(self) -> Optional[ExecutionRequest]:
        with self._lock:
            now = self._clock.now_timestamp()
            temp_held = []
            result: Optional[ExecutionRequest] = None

            while self._queue:
                neg_prio, avail_time, seq, req = heapq.heappop(self._queue)
                if avail_time <= now:
                    result = req
                    break
                else:
                    temp_held.append((neg_prio, avail_time, seq, req))

            # Put back delayed tasks
            for item in temp_held:
                heapq.heappush(self._queue, item)

            return result

    def requeue_for_retry(self, request: ExecutionRequest, delay_seconds: float = 0.0) -> None:
        with self._lock:
            self._sequence += 1
            avail_time = self._clock.now_timestamp() + delay_seconds
            heapq.heappush(self._queue, (-request.task.priority, avail_time, self._sequence, request))

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def get_by_idempotency_key(self, key: IdempotencyKey) -> Optional[ExecutionRequest]:
        with self._lock:
            return self._idempotency_map.get(str(key))
