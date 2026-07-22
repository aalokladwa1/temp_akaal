"""
Operations Replay Engine.
Provides read-only playback of historical operational timelines, alerts, and incidents.
"""

from typing import Dict, List, Any
from threading import RLock


class OperationsReplayEngine:
    """Read-only replay engine for timeline reconstruction and incident analysis."""

    def __init__(self, timeline_history=None) -> None:
        self._lock = RLock()
        self.timeline_history = timeline_history

    def replay_time_window(self, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """Replays events within a specific time window."""
        with self._lock:
            if not self.timeline_history or not hasattr(self.timeline_history, "get_timeline"):
                return []
            events = self.timeline_history.get_timeline()
            return [e for e in events if start_time <= e.get("timestamp", 0.0) <= end_time]

    def replay_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Replays events matching a specific correlation ID."""
        with self._lock:
            if not self.timeline_history or not hasattr(self.timeline_history, "get_timeline"):
                return []
            events = self.timeline_history.get_timeline()
            return [e for e in events if e.get("correlation_id") == correlation_id]
