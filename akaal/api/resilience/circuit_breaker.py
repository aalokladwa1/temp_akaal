"""
Circuit Breaker & Bulkhead Semaphore Engine for AKAAL Platform 7.
"""

from typing import Any, Callable, Coroutine, Dict, Optional, TypeVar
import asyncio
import time

from akaal.api.contracts.errors import CircuitBreakerOpenError

T = TypeVar("T")


class CircuitBreaker:
    """Production Circuit Breaker State Machine with Bulkhead Semaphore."""

    def __init__(
        self,
        name: str,
        failure_threshold: float = 0.5,
        recovery_timeout_s: float = 10.0,
        max_concurrency: int = 100,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.semaphore = asyncio.Semaphore(max_concurrency)

        self.state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count: int = 0
        self.success_count: int = 0
        self.total_count: int = 0
        self.last_state_change: float = time.time()

    async def execute(self, func: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any) -> T:
        now = time.time()

        if self.state == "OPEN":
            if now - self.last_state_change > self.recovery_timeout_s:
                self.state = "HALF_OPEN"
                self.last_state_change = now
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit Breaker '{self.name}' is OPEN. Requests blocked to prevent cascading failures.",
                    details={"circuit": self.name, "recovery_in_seconds": self.recovery_timeout_s - (now - self.last_state_change)},
                )

        async with self.semaphore:
            try:
                res = await func(*args, **kwargs)
                self._on_success()
                return res
            except Exception as e:
                self._on_failure()
                raise e

    def _on_success(self) -> None:
        self.total_count += 1
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= 3:
                self.state = "CLOSED"
                self.failure_count = 0
                self.total_count = 0
                self.last_state_change = time.time()

    def _on_failure(self) -> None:
        self.total_count += 1
        self.failure_count += 1
        if self.total_count >= 5:
            fail_rate = self.failure_count / self.total_count
            if fail_rate >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = time.time()
