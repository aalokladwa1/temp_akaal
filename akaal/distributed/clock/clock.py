"""
Clock Abstraction for Enterprise Distributed Runtime.
Removes direct system time dependencies from time-sensitive components,
enabling fully deterministic unit, concurrency, and time-warping tests.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import time
from typing import Optional


class Clock(ABC):
    """Abstract Clock interface for UTC, monotonic time, and sleep abstractions."""

    @abstractmethod
    def now_utc(self) -> datetime:
        """Return current datetime in UTC."""
        pass

    @abstractmethod
    def now_timestamp(self) -> float:
        """Return current UTC timestamp in seconds."""
        pass

    @abstractmethod
    def monotonic(self) -> float:
        """Return monotonic time in seconds."""
        pass

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        """Sleep for specified seconds."""
        pass


class SystemClock(Clock):
    """Production System Clock implementation."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def now_timestamp(self) -> float:
        return datetime.now(timezone.utc).timestamp()

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class TestClock(Clock):
    """
    Deterministic Test Clock for time simulation and time-warping tests.
    """
    __test__ = False

    def __init__(self, initial_timestamp: Optional[float] = None) -> None:
        self._current_timestamp = initial_timestamp if initial_timestamp is not None else 1700000000.0
        self._monotonic_time = 0.0

    def now_utc(self) -> datetime:
        return datetime.fromtimestamp(self._current_timestamp, tz=timezone.utc)

    def now_timestamp(self) -> float:
        return self._current_timestamp

    def monotonic(self) -> float:
        return self._monotonic_time

    def sleep(self, seconds: float) -> None:
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        """Advance test clock by specified seconds."""
        if seconds < 0:
            raise ValueError("Cannot advance test clock backwards.")
        self._current_timestamp += seconds
        self._monotonic_time += seconds
