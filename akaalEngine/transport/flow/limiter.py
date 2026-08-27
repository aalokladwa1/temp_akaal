"""
akaalEngine.transport.flow.limiter
==================================
TokenBucketBandwidthLimiter with COOPERATIVE_RATE_WAIT semantics and time.monotonic().
"""

from threading import RLock
import time
from typing import Optional, Any

from akaalEngine.transport.models.errors import TransportCancelledError


class TokenBucketBandwidthLimiter:
    """
    Thread-safe Token Bucket Bandwidth Limiter.
    Uses COOPERATIVE_RATE_WAIT in bounded 50ms slices outside locks, time.monotonic(), and cancellation checks.
    """

    def __init__(self, rate_bytes_per_sec: int = 0) -> None:
        self.rate_bytes_per_sec = rate_bytes_per_sec  # 0 = unlimited
        self.tokens = float(rate_bytes_per_sec) if rate_bytes_per_sec > 0 else 0.0
        self.max_tokens = float(rate_bytes_per_sec) if rate_bytes_per_sec > 0 else 0.0
        self.last_update = time.monotonic()
        self._lock = RLock()
        self.cooperative_wait_seconds_total = 0.0

    def set_rate(self, rate_bytes_per_sec: int) -> None:
        """Dynamically adjusts bandwidth rate limit."""
        with self._lock:
            self.rate_bytes_per_sec = rate_bytes_per_sec
            if rate_bytes_per_sec > 0:
                self.max_tokens = float(rate_bytes_per_sec)
                self.tokens = min(self.tokens, self.max_tokens)
            else:
                self.max_tokens = 0.0
                self.tokens = 0.0

    def consume(self, bytes_count: int, cancellation_token: Optional[Any] = None) -> None:
        """
        Consumes tokens for payload bytes.
        If insufficient tokens exist, performs COOPERATIVE_RATE_WAIT in 50ms slices outside locks.
        """
        if self.rate_bytes_per_sec <= 0 or bytes_count <= 0:
            return

        while True:
            if cancellation_token and getattr(cancellation_token, "is_cancelled", False):
                raise TransportCancelledError("Cancelled during bandwidth rate wait")

            wait_time = 0.0
            with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now

                # Add generated tokens, bounded by max_tokens burst cap
                self.tokens = min(self.max_tokens, self.tokens + (elapsed * self.rate_bytes_per_sec))

                if self.tokens >= bytes_count:
                    self.tokens -= bytes_count
                    return
                else:
                    needed = bytes_count - self.tokens
                    wait_time = needed / float(self.rate_bytes_per_sec)

            # Perform cooperative sleep outside of lock in bounded 50ms slices
            slice_time = min(wait_time, 0.05)
            time.sleep(slice_time)

            with self._lock:
                self.cooperative_wait_seconds_total += slice_time
