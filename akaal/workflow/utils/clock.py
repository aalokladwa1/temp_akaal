"""Deterministic Time Providers for AKAAL Workflow Platform."""

from datetime import datetime, timezone
import time
from typing import Protocol


class IClock(Protocol):
    """Abstract interface for deterministic time operations."""
    
    def now_utc(self) -> str:
        """Return ISO 8601 formatted UTC timestamp string."""
        ...
        
    def monotonic(self) -> float:
        """Return monotonic timer value in seconds."""
        ...
        
    def timestamp(self) -> float:
        """Return current POSIX timestamp in seconds."""
        ...


class SystemClock:
    """Production system clock using standard system time APIs."""
    
    def now_utc(self) -> str:
        return datetime.now(timezone.utc).isoformat()
        
    def monotonic(self) -> float:
        return time.monotonic()
        
    def timestamp(self) -> float:
        return time.time()


class FixedClock:
    """Deterministic fixed clock for testing and reproducible replay runs."""
    
    def __init__(
        self,
        fixed_iso: str = "2026-01-01T00:00:00+00:00",
        fixed_timestamp: float = 1767225600.0,
        fixed_monotonic: float = 1000.0,
        auto_increment_seconds: float = 0.0,
    ) -> None:
        self._iso = fixed_iso
        self._timestamp = fixed_timestamp
        self._monotonic = fixed_monotonic
        self._increment = auto_increment_seconds

    def now_utc(self) -> str:
        val = self._iso
        if self._increment > 0:
            self._timestamp += self._increment
            self._monotonic += self._increment
            self._iso = datetime.fromtimestamp(self._timestamp, timezone.utc).isoformat()
        return val

    def monotonic(self) -> float:
        val = self._monotonic
        if self._increment > 0:
            self._monotonic += self._increment
            self._timestamp += self._increment
        return val

    def timestamp(self) -> float:
        val = self._timestamp
        if self._increment > 0:
            self._timestamp += self._increment
            self._monotonic += self._increment
        return val
