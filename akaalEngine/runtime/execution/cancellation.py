"""
akaalEngine.runtime.execution.cancellation
==========================================
Cooperative cancellation tokens and physical execution pause gates.
"""

from threading import Event, RLock
import time
from typing import Optional


class CancellationToken:
    """
    Cooperative thread/process cancellation token.
    Allows workers and tasks to safely observe cancellation signals.
    """

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self._event = Event()
        self._reason: Optional[str] = None
        self._cancel_time: Optional[float] = None
        self._lock = RLock()

    def cancel(self, reason: str = "Cancellation requested") -> None:
        with self._lock:
            if not self._event.is_set():
                self._reason = reason
                self._cancel_time = time.time()
                self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> Optional[str]:
        with self._lock:
            return self._reason

    def check(self) -> None:
        """Throws TaskExecutionError if cancellation was signaled."""
        if self.is_cancelled:
            from akaalEngine.runtime.models.errors import TaskExecutionError
            raise TaskExecutionError(self.task_id, f"Cancelled: {self.reason}")

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._event.wait(timeout)


class PauseGate:
    """
    Cooperative physical pause gate.
    Executors wait on this gate during PAUSED state.
    """

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self._event = Event()
        self._event.set()  # Set means NOT paused (unblocked)
        self._lock = RLock()

    def pause(self) -> None:
        with self._lock:
            self._event.clear()

    def resume(self) -> None:
        with self._lock:
            self._event.set()

    @property
    def is_paused(self) -> bool:
        return not self._event.is_set()

    def wait_if_paused(self, timeout: Optional[float] = None) -> bool:
        """Blocks thread execution if gate is paused until resumed or timeout expires."""
        return self._event.wait(timeout)
