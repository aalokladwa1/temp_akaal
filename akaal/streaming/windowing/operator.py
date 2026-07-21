"""
WindowOperator state aggregator module for Platform 3.
Accumulates records per window and triggers window evaluation on watermark progress.
"""

from typing import Dict, List, Tuple, Optional, Any
from threading import RLock
import logging

from akaal.streaming.domain.models import StreamRecord, Watermark, StreamWindow
from akaal.streaming.domain.identifiers import WindowId
from akaal.streaming.windowing.assigner import WindowAssigner

logger = logging.getLogger("nexusforge.streaming.window_operator")


class WindowOperator:
    """
    Stateful WindowOperator collecting records into assigned windows and evaluating them on Watermark arrival.
    """

    def __init__(self, assigner: WindowAssigner) -> None:
        self._lock = RLock()
        self.assigner = assigner
        self._window_state: Dict[str, Tuple[StreamWindow, List[StreamRecord]]] = {}

    def process_record(self, record: StreamRecord) -> None:
        """Assign record to windows and store in window state."""
        with self._lock:
            assigned = self.assigner.assign_windows(record)
            for window in assigned:
                w_key = str(window.window_id)
                if w_key not in self._window_state:
                    self._window_state[w_key] = (window, [])
                self._window_state[w_key][1].append(record)

    def trigger_watermark(self, watermark: Watermark) -> List[Tuple[StreamWindow, List[StreamRecord]]]:
        """Trigger and return records for all windows whose end_time <= watermark.timestamp."""
        with self._lock:
            triggered: List[Tuple[StreamWindow, List[StreamRecord]]] = []
            keys_to_remove = []

            for w_key, (window, records) in self._window_state.items():
                if window.end_time <= watermark.timestamp:
                    triggered.append((window, records))
                    keys_to_remove.append(w_key)

            for key in keys_to_remove:
                self._window_state.pop(key, None)

            if triggered:
                logger.info(f"Triggered {len(triggered)} windows on Watermark {watermark.timestamp}.")

            return triggered
