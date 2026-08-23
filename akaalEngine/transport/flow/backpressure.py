"""
akaalEngine.transport.flow.backpressure
========================================
BoundedStreamBuffer enforcing max_batches, max_rows, max_bytes concurrent limits and FSM states.
Mined from `akaal/streaming/` & `akaal/performance/optimizers/backpressure.py`.
"""

from collections import deque
from enum import Enum
import logging
from threading import Condition, RLock
from typing import Any, List, Optional

from akaalEngine.transport.models.batch import TransportBatch
from akaalEngine.transport.models.errors import TransportCancelledError, TransportError
from akaalEngine.transport.models.spec import TransportTuningPolicy

logger = logging.getLogger("akaalEngine.transport.flow.backpressure")


class BufferState(str, Enum):
    OPEN = "OPEN"
    DRAINING = "DRAINING"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    CLOSED = "CLOSED"


class BoundedStreamBuffer:
    """
    Thread-safe BoundedStreamBuffer enforcing concurrent bounds over max_batches, max_rows, and max_bytes.
    Executes FSM state transitions (OPEN, DRAINING, CANCELLED, FAILED, CLOSED) and wakes blocked threads.
    """

    def __init__(self, tuning_policy: Optional[TransportTuningPolicy] = None) -> None:
        policy = tuning_policy or TransportTuningPolicy()
        self.max_batches = policy.max_queue_batches
        self.max_rows = policy.max_queue_rows
        self.max_bytes = policy.max_queue_bytes

        self._lock = RLock()
        self._not_full = Condition(self._lock)
        self._not_empty = Condition(self._lock)

        self._queue: deque[TransportBatch] = deque()
        self.current_rows = 0
        self.current_bytes = 0
        self.state = BufferState.OPEN

    def push(self, batch: TransportBatch, cancellation_token: Optional[Any] = None) -> None:
        """Pushes a batch into buffer. Blocks if queue capacity is reached. Rejects admission during DRAINING/CLOSED."""
        with self._lock:
            while (
                len(self._queue) >= self.max_batches
                or self.current_rows + batch.metadata.row_count > self.max_rows
                or self.current_bytes + batch.metadata.size_bytes > self.max_bytes
            ):
                if self.state != BufferState.OPEN:
                    raise TransportError(f"Cannot push batch: buffer state is '{self.state.value}'")

                if cancellation_token and getattr(cancellation_token, "is_cancelled", False):
                    self.state = BufferState.CANCELLED
                    self._not_empty.notify_all()
                    raise TransportCancelledError("Push cancelled while waiting for buffer capacity")

                self._not_full.wait(timeout=0.1)

            if self.state != BufferState.OPEN:
                raise TransportError(f"Cannot push batch: buffer state is '{self.state.value}'")

            self._queue.append(batch)
            self.current_rows += batch.metadata.row_count
            self.current_bytes += batch.metadata.size_bytes
            self._not_empty.notify()

    def pop(self, cancellation_token: Optional[Any] = None, timeout: float = 0.5) -> Optional[TransportBatch]:
        """Pops a batch from buffer. Blocks if empty. Returns None when buffer is drained and closed."""
        with self._lock:
            while not self._queue:
                if self.state in (BufferState.CLOSED, BufferState.DRAINING) and not self._queue:
                    return None

                if self.state == BufferState.CANCELLED:
                    raise TransportCancelledError("Buffer cancelled")

                if self.state == BufferState.FAILED:
                    raise TransportError("Buffer in failed state")

                if cancellation_token and getattr(cancellation_token, "is_cancelled", False):
                    raise TransportCancelledError("Pop cancelled while waiting for batch")

                got_batch = self._not_empty.wait(timeout=timeout)
                if not got_batch and not self._queue:
                    if self.state in (BufferState.CLOSED, BufferState.DRAINING):
                        return None

            batch = self._queue.popleft()
            self.current_rows -= batch.metadata.row_count
            self.current_bytes -= batch.metadata.size_bytes
            self._not_full.notify()
            return batch

    def set_draining(self) -> None:
        with self._lock:
            if self.state == BufferState.OPEN:
                self.state = BufferState.DRAINING
                self._not_full.notify_all()
                self._not_empty.notify_all()

    def set_cancelled(self) -> None:
        with self._lock:
            self.state = BufferState.CANCELLED
            self._not_full.notify_all()
            self._not_empty.notify_all()

    def set_failed(self) -> None:
        with self._lock:
            self.state = BufferState.FAILED
            self._not_full.notify_all()
            self._not_empty.notify_all()

    def close(self) -> None:
        with self._lock:
            self.state = BufferState.CLOSED
            self._not_full.notify_all()
            self._not_empty.notify_all()
