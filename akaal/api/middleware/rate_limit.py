"""
Multi-Tier Distributed / Local Memory Rate Limiter.
"""

from typing import Dict, Tuple
import time

from akaal.api.contracts.errors import RateLimitExceededError


class RateLimiter:
    """Sliding Window Rate Limiter supporting User, Tenant, IP, and API-Key quotas."""

    def __init__(self, requests_per_window: int = 100, window_seconds: int = 60) -> None:
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        # Key -> List of timestamps
        self._history: Dict[str, list] = {}

    def check_rate_limit(self, key: str) -> Tuple[int, int, int]:
        """
        Check rate limit for given key.
        Returns (limit, remaining, reset_seconds).
        Raises RateLimitExceededError if quota breached.
        """
        now = time.time()
        cutoff = now - self.window_seconds

        if key not in self._history:
            self._history[key] = []

        # Prune expired timestamps
        self._history[key] = [t for t in self._history[key] if t > cutoff]

        current_count = len(self._history[key])
        remaining = max(0, self.requests_per_window - current_count)
        reset_seconds = self.window_seconds

        if current_count >= self.requests_per_window:
            raise RateLimitExceededError(
                f"Rate limit exceeded for key '{key}'. Limit: {self.requests_per_window} req / {self.window_seconds}s",
                details={"key": key, "limit": self.requests_per_window, "retry_after": reset_seconds},
            )

        self._history[key].append(now)
        return self.requests_per_window, remaining - 1, reset_seconds
