"""Backpressure Controller for Adaptive Load Shedding and Throttling."""

import threading


class BackpressureController:
    """Monitors platform queue depth and system load, triggering adaptive throttling."""

    def __init__(self, high_watermark_queue_depth: int = 1000) -> None:
        self.high_watermark = high_watermark_queue_depth
        self._is_throttled: bool = False
        self._lock = threading.Lock()

    def update_metrics(self, current_queue_depth: int) -> bool:
        """Update system metrics and return True if backpressure is active."""
        with self._lock:
            self._is_throttled = current_queue_depth >= self.high_watermark
            return self._is_throttled

    @property
    def is_throttled(self) -> bool:
        with self._lock:
            return self._is_throttled
