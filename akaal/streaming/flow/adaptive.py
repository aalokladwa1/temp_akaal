"""
Adaptive Streaming Subsystem for Platform 3.
Provides dynamic batch size tuning and runtime throughput optimization.
"""

from threading import RLock
import logging

logger = logging.getLogger("nexusforge.streaming.adaptive_tuner")


class AdaptiveStreamTuner:
    """
    AdaptiveStreamTuner adjusting dynamic batch sizes based on observed latency and throughput.
    """

    def __init__(self, initial_batch_size: int = 100, min_batch_size: int = 10, max_batch_size: int = 5000) -> None:
        self._lock = RLock()
        self.current_batch_size = initial_batch_size
        self.min_batch = min_batch_size
        self.max_batch = max_batch_size
        self._history_latencies: List[float] = []

    def record_execution(self, processed_records_count: int, latency_seconds: float) -> int:
        """Update tuner metrics and compute next optimal batch size."""
        with self._lock:
            if processed_records_count <= 0 or latency_seconds <= 0:
                return self.current_batch_size

            self._history_latencies.append(latency_seconds)
            if len(self._history_latencies) > 100:
                self._history_latencies.pop(0)

            # High latency (> 100ms): decrease batch size to maintain responsiveness
            if latency_seconds > 0.1:
                self.current_batch_size = max(self.min_batch, int(self.current_batch_size * 0.8))
            # Low latency (< 10ms): increase batch size for higher throughput
            elif latency_seconds < 0.01:
                self.current_batch_size = min(self.max_batch, int(self.current_batch_size * 1.2))

            return self.current_batch_size
