"""
Flow Control & Backpressure Subsystem for Platform 3.
Provides end-to-end backpressure, adaptive throttling, and bounded queue congestion management.
"""

from threading import RLock
import time
import logging

from akaal.streaming.domain.enums import BackpressureState
from akaal.streaming.domain.errors import BackpressureError

logger = logging.getLogger("nexusforge.streaming.backpressure")


class BackpressureController:
    """
    Thread-safe BackpressureController monitoring buffer levels and applying adaptive throttling.
    """

    def __init__(
        self,
        max_queue_capacity: int = 1000,
        high_watermark_ratio: float = 0.8,
        low_watermark_ratio: float = 0.2,
    ) -> None:
        self._lock = RLock()
        self.max_capacity = max_queue_capacity
        self.high_watermark = int(max_queue_capacity * high_watermark_ratio)
        self.low_watermark = int(max_queue_capacity * low_watermark_ratio)
        self._current_size = 0
        self._state = BackpressureState.NORMAL

    def check_and_update(self, current_queue_size: int) -> BackpressureState:
        """Evaluates current queue size against watermarks and returns updated BackpressureState."""
        with self._lock:
            self._current_size = current_queue_size

            if self._current_size >= self.max_capacity:
                self._state = BackpressureState.THROTTLED
                logger.warning(f"Backpressure HIGH BOUND HIT ({self._current_size}/{self.max_capacity}). Throttling upstream.")
            elif self._current_size >= self.high_watermark:
                self._state = BackpressureState.HIGH_WATERMARK
            elif self._current_size <= self.low_watermark:
                self._state = BackpressureState.NORMAL
            else:
                if self._state == BackpressureState.THROTTLED and self._current_size < self.high_watermark:
                    self._state = BackpressureState.LOW_WATERMARK

            return self._state

    def apply_throttling(self) -> float:
        """
        Calculates sleep delay in seconds based on backpressure state.
        Returns calculated sleep time.
        """
        with self._lock:
            if self._state == BackpressureState.THROTTLED:
                delay = 0.05  # 50ms throttle delay
            elif self._state == BackpressureState.HIGH_WATERMARK:
                delay = 0.01  # 10ms throttle delay
            else:
                delay = 0.0

            if delay > 0:
                time.sleep(delay)
            return delay

    @property
    def state(self) -> BackpressureState:
        with self._lock:
            return self._state
