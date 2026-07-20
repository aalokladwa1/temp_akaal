"""Retry and Timeout Policy Abstractions and Reference Implementations."""

import concurrent.futures
from typing import Callable, Protocol, TypeVar
import time

T = TypeVar("T")


class IRetryPolicy(Protocol):
    """Abstract interface for workflow step retry evaluation."""

    def should_retry(self, attempt: int, max_retries: int, exception: Exception) -> bool:
        """Determine if a failed step should be retried."""
        ...

    def get_delay_seconds(self, attempt: int) -> float:
        """Calculate backoff delay seconds for the retry attempt."""
        ...


class ExponentialRetryPolicy:
    """Exponential backoff retry policy with jitter multiplier."""

    def __init__(self, initial_delay_seconds: float = 1.0, max_delay_seconds: float = 60.0, backoff_factor: float = 2.0) -> None:
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_factor = backoff_factor

    def should_retry(self, attempt: int, max_retries: int, exception: Exception) -> bool:
        return attempt < max_retries

    def get_delay_seconds(self, attempt: int) -> float:
        delay = self.initial_delay_seconds * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


class FixedRetryPolicy:
    """Fixed delay retry policy."""

    def __init__(self, delay_seconds: float = 1.0) -> None:
        self.delay_seconds = delay_seconds

    def should_retry(self, attempt: int, max_retries: int, exception: Exception) -> bool:
        return attempt < max_retries

    def get_delay_seconds(self, attempt: int) -> float:
        return self.delay_seconds


class NoRetryPolicy:
    """Policy disabling retries."""

    def should_retry(self, attempt: int, max_retries: int, exception: Exception) -> bool:
        return False

    def get_delay_seconds(self, attempt: int) -> float:
        return 0.0


class ITimeoutPolicy(Protocol):
    """Abstract interface for step execution deadline enforcement."""

    def execute_with_timeout(self, func: Callable[[], T], timeout_seconds: float) -> T:
        """Execute callable under strict timeout limit."""
        ...


class FixedTimeoutPolicy:
    """Timeout policy enforcing execution bounds via ThreadPoolExecutor."""

    def execute_with_timeout(self, func: Callable[[], T], timeout_seconds: float) -> T:
        if timeout_seconds <= 0:
            return func()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            try:
                return future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError as err:
                raise TimeoutError(f"Execution timed out after {timeout_seconds} seconds.") from err


class NoTimeoutPolicy:
    """Policy disabling timeout limits."""

    def execute_with_timeout(self, func: Callable[[], T], timeout_seconds: float) -> T:
        return func()
