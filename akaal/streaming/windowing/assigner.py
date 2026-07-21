"""
Window Processing: WindowAssigners for Tumbling, Sliding, and Session Windows.
"""

from abc import ABC, abstractmethod
from typing import List
from threading import RLock

from akaal.streaming.domain.identifiers import WindowId
from akaal.streaming.domain.enums import WindowType
from akaal.streaming.domain.models import StreamRecord, StreamWindow


class WindowAssigner(ABC):
    """Abstract WindowAssigner interface."""
    @abstractmethod
    def assign_windows(self, record: StreamRecord) -> List[StreamWindow]:
        pass


class TumblingWindowAssigner(WindowAssigner):
    """Fixed non-overlapping window assigner."""

    def __init__(self, window_size_seconds: float) -> None:
        if window_size_seconds <= 0:
            raise ValueError("Window size must be positive.")
        self.window_size = window_size_seconds

    def assign_windows(self, record: StreamRecord) -> List[StreamWindow]:
        ts = record.event_time
        start = (ts // self.window_size) * self.window_size
        end = start + self.window_size
        w_id = WindowId(f"tumbling_{int(start)}_{int(end)}")
        return [
            StreamWindow(
                window_id=w_id,
                window_type=WindowType.TUMBLING,
                start_time=start,
                end_time=end,
            )
        ]


class SlidingWindowAssigner(WindowAssigner):
    """Sliding overlapping window assigner."""

    def __init__(self, window_size_seconds: float, slide_seconds: float) -> None:
        if window_size_seconds <= 0 or slide_seconds <= 0:
            raise ValueError("Window size and slide must be positive.")
        self.window_size = window_size_seconds
        self.slide = slide_seconds

    def assign_windows(self, record: StreamRecord) -> List[StreamWindow]:
        ts = record.event_time
        last_start = (ts // self.slide) * self.slide
        windows: List[StreamWindow] = []

        start = last_start
        while start > (ts - self.window_size):
            end = start + self.window_size
            if ts >= start and ts < end:
                w_id = WindowId(f"sliding_{int(start)}_{int(end)}")
                windows.append(
                    StreamWindow(
                        window_id=w_id,
                        window_type=WindowType.SLIDING,
                        start_time=start,
                        end_time=end,
                    )
                )
            start -= self.slide

        return windows


class SessionWindowAssigner(WindowAssigner):
    """Gap-based session window assigner."""

    def __init__(self, session_gap_seconds: float) -> None:
        if session_gap_seconds <= 0:
            raise ValueError("Session gap must be positive.")
        self.session_gap = session_gap_seconds

    def assign_windows(self, record: StreamRecord) -> List[StreamWindow]:
        start = record.event_time
        end = start + self.session_gap
        w_id = WindowId(f"session_{int(start)}_{int(end)}")
        return [
            StreamWindow(
                window_id=w_id,
                window_type=WindowType.SESSION,
                start_time=start,
                end_time=end,
            )
        ]
