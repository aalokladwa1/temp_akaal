"""akaalPipeline.ports.clock
===========================
ClockPort abstraction for all expiry, lease, and deadline logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class ClockPort(ABC):
    @abstractmethod
    def now_iso(self) -> str:
        """Return current UTC timestamp in ISO 8601 string format."""


class SystemClock(ClockPort):
    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


class TestClock(ClockPort):
    def __init__(self, initial_iso: str = "2026-08-20T20:00:00+00:00") -> None:
        self._current = initial_iso

    def set_time(self, new_iso: str) -> None:
        self._current = new_iso

    def now_iso(self) -> str:
        return self._current
