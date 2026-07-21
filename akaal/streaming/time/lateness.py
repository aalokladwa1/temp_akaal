"""
Late-Event Handling & AllowedLateness Subsystem.
Enables side-output routing for events arriving after current watermark.
"""

from typing import List, Optional, Tuple
from threading import RLock
import logging

from akaal.streaming.domain.models import StreamRecord, Watermark

logger = logging.getLogger("nexusforge.streaming.lateness")


class AllowedLateness:
    """
    Manages allowed lateness threshold and filters/routes late events.
    """

    def __init__(self, allowed_lateness_seconds: float = 10.0) -> None:
        self._lock = RLock()
        self.allowed_lateness_seconds = allowed_lateness_seconds
        self._late_events_side_output: List[StreamRecord] = []

    def is_late(self, record: StreamRecord, current_watermark: Watermark) -> bool:
        """True if record event_time is strictly less than current_watermark.timestamp."""
        with self._lock:
            return record.event_time < current_watermark.timestamp

    def handle_record(self, record: StreamRecord, current_watermark: Watermark) -> bool:
        """
        Evaluates record against watermark:
        Returns True if record should be processed (within allowed lateness).
        Returns False and routes to side-output if record exceeds allowed lateness.
        """
        with self._lock:
            if not self.is_late(record, current_watermark):
                return True

            lateness = current_watermark.timestamp - record.event_time
            if lateness <= self.allowed_lateness_seconds:
                logger.debug(f"Late record (lateness {lateness:.2f}s) within allowed lateness ({self.allowed_lateness_seconds}s). Processing.")
                return True

            logger.warning(f"Record event_time {record.event_time} exceeds watermark {current_watermark.timestamp} + lateness {self.allowed_lateness_seconds}s. Routing to side-output.")
            self._late_events_side_output.append(record)
            return False

    def get_and_clear_late_side_outputs(self) -> List[StreamRecord]:
        """Retrieve and clear late event side-output records."""
        with self._lock:
            out = list(self._late_events_side_output)
            self._late_events_side_output.clear()
            return out
