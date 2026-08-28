"""akaal.core.time_authority
==========================
Canonical Time Authority.
Provides monotonic clock for in-process durations and UTC wall clock for persisted records.
Detects clock rollback and excessive skew.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional


class ClockSkewDetectedError(RuntimeError):
    """Raised when system wall clock rolls backward or suffers excessive skew."""
    pass


class TimeAuthority:
    """Canonical system time authority."""

    _last_wall_utc_ts: float = 0.0
    _last_monotonic_ts: float = 0.0
    _max_backward_skew_seconds: float = 5.0

    @classmethod
    def set_clock_skew_threshold(cls, threshold_seconds: float) -> None:
        """Configure maximum allowable backward wall clock drift."""
        if threshold_seconds < 0.1 or threshold_seconds > 60.0:
            raise ValueError("Clock skew threshold must be between 0.1s and 60.0s")
        cls._max_backward_skew_seconds = threshold_seconds

    @classmethod
    def get_clock_skew_threshold(cls) -> float:
        """Get current clock skew threshold in seconds."""
        return cls._max_backward_skew_seconds

    @classmethod
    def monotonic_now(cls) -> float:
        """Returns monotonic time in seconds for timeouts and lease durations."""
        return time.monotonic()

    @classmethod
    def utc_now(cls) -> datetime:
        """Returns current timezone-aware UTC datetime. Detects clock rollback."""
        now = datetime.now(timezone.utc)
        now_ts = now.timestamp()
        mono = time.monotonic()

        if cls._last_wall_utc_ts > 0.0:
            elapsed_mono = mono - cls._last_monotonic_ts
            # If wall clock went backwards by more than allowed skew
            if (now_ts + cls._max_backward_skew_seconds) < cls._last_wall_utc_ts:
                raise ClockSkewDetectedError(
                    f"Wall clock rollback detected: current {now_ts} < previous {cls._last_wall_utc_ts}"
                )

        cls._last_wall_utc_ts = now_ts
        cls._last_monotonic_ts = mono
        return now

    @classmethod
    def utc_iso_now(cls) -> str:
        """Returns current UTC ISO-8601 formatted string."""
        return cls.utc_now().isoformat()

    @classmethod
    def parse_iso(cls, ts_str: str) -> datetime:
        """Parse ISO-8601 timestamp to UTC datetime."""
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @classmethod
    def is_expired(cls, expires_at_iso: Optional[str]) -> bool:
        """Check if an ISO timestamp has expired against current UTC wall clock."""
        if expires_at_iso is None:
            return False
        dt = cls.parse_iso(expires_at_iso)
        return cls.utc_now() >= dt
