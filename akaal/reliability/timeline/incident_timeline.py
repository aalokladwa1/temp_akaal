"""Incident Timeline Engine: Chronological lifecycle tracking for incidents."""

import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class IncidentTimelineEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str = "inc_default"
    event_type: str = "FAILURE_DETECTED"
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class IncidentTimelineEngine:
    """Thread-safe engine capturing microsecond-ordered incident lifecycle events."""

    def __init__(self):
        self._events: List[IncidentTimelineEvent] = []
        self._lock = threading.RLock()

    def record_event(self, incident_id: str, event_type: str, details: Dict[str, Any]) -> IncidentTimelineEvent:
        with self._lock:
            event = IncidentTimelineEvent(
                incident_id=incident_id,
                event_type=event_type,
                timestamp=time.time(),
                details=details,
            )
            self._events.append(event)
            return event

    def get_timeline(self, incident_id: str) -> List[IncidentTimelineEvent]:
        with self._lock:
            return [ev for ev in self._events if ev.incident_id == incident_id]

    def list_all_events(self) -> List[IncidentTimelineEvent]:
        with self._lock:
            return list(self._events)
