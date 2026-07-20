"""Sliding Window Rate Limiter Middleware for API Gateway."""

import threading
from typing import Dict, List, Tuple
from akaal.workflow.utils.clock import IClock, SystemClock


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter enforcing request rate limits per tenant/IP."""

    def __init__(self, limit: int = 100, window_seconds: float = 60.0, clock: IClock | None = None) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock or SystemClock()
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check_rate_limit(self, client_id: str) -> Tuple[bool, int]:
        """Check if request is allowed under sliding window limit. Returns (allowed, remaining)."""
        with self._lock:
            now = float(self._clock.monotonic())
            cutoff = now - self.window_seconds
            timestamps = self._requests.get(client_id, [])
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= self.limit:
                self._requests[client_id] = valid_timestamps
                return False, 0

            valid_timestamps.append(now)
            self._requests[client_id] = valid_timestamps
            return True, self.limit - len(valid_timestamps)
