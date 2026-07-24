"""
AKAAL Platform 7 — Incident Timeline Manager.
"""

from typing import Dict, List, Any
import datetime


class IncidentTimelineManager:
    """Records timeline events during active incident response."""

    def __init__(self) -> None:
        self._timeline_events: Dict[str, List[Dict[str, Any]]] = {}

    def add_timeline_event(self, incident_id: str, author: str, message: str, event_type: str = "STATUS_UPDATE") -> Dict[str, Any]:
        if incident_id not in self._timeline_events:
            self._timeline_events[incident_id] = []

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        event = {
            "timestamp": now,
            "author": author,
            "message": message,
            "event_type": event_type,
        }
        self._timeline_events[incident_id].append(event)
        return event

    def get_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        return self._timeline_events.get(incident_id, [])
