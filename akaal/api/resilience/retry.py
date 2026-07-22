"""
Exponential Backoff with Full Jitter Retry Helper.
"""

from typing import Any, Callable, Coroutine, Type, TypeVar
import asyncio
import random

T = TypeVar("T")


class RetryPolicy:
    """Configurable Exponential Backoff Retry with Full Jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_s: float = 0.1,
        max_delay_s: float = 2.0,
        retryable_exceptions: Type[BaseException] = Exception,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s
        self.max_delay_s = max_delay_s
        self.retryable_exceptions = retryable_exceptions

    async def execute(self, func: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any) -> T:
        last_exc: Exception = Exception("Unknown execution failure")
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.retryable_exceptions as e:
                last_exc = e
                if attempt == self.max_retries:
                    break
                # Full jitter computation
                temp = min(self.max_delay_s, self.base_delay_s * (2 ** attempt))
                sleep_time = random.uniform(0, temp)
                await asyncio.sleep(sleep_time)
        raise last_exc
