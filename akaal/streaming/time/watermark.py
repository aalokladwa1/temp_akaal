"""
Event-Time Processing & Watermark Generator Subsystem.
Provides event timestamp extraction, bounded out-of-orderness watermarking, and watermark propagation.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from threading import RLock

from akaal.streaming.domain.models import StreamRecord, Watermark
from akaal.streaming.domain.errors import WatermarkError


class EventTimeExtractor(ABC):
    """Abstract EventTimeExtractor interface."""
    @abstractmethod
    def extract_timestamp(self, record: StreamRecord) -> float:
        pass


class DefaultEventTimeExtractor(EventTimeExtractor):
    """Extracts event_time directly from StreamRecord.event_time."""
    def extract_timestamp(self, record: StreamRecord) -> float:
        return record.event_time


class WatermarkGenerator(ABC):
    """Abstract WatermarkGenerator interface."""
    @abstractmethod
    def on_record(self, record: StreamRecord) -> Optional[Watermark]:
        pass

    @abstractmethod
    def current_watermark(self) -> Watermark:
        pass


class BoundedOutOfOrdernessWatermark(WatermarkGenerator):
    """
    Bounded Out-Of-Orderness Watermark generator.
    Maintains max observed event time minus allowed_out_of_orderness_seconds.
    Guarantees monotonically non-decreasing watermarks.
    """

    def __init__(self, max_out_of_orderness_seconds: float = 5.0) -> None:
        self._lock = RLock()
        self._max_out_of_orderness = max_out_of_orderness_seconds
        self._max_event_time = 0.0
        self._current_watermark_time = 0.0

    def on_record(self, record: StreamRecord) -> Optional[Watermark]:
        with self._lock:
            if record.event_time > self._max_event_time:
                self._max_event_time = record.event_time

            new_wm_time = max(0.0, self._max_event_time - self._max_out_of_orderness)
            if new_wm_time > self._current_watermark_time:
                self._current_watermark_time = new_wm_time
                return Watermark(timestamp=self._current_watermark_time)

            return None

    def current_watermark(self) -> Watermark:
        with self._lock:
            return Watermark(timestamp=self._current_watermark_time)
