"""
Optimization History Auditor Tracker.
"""

from typing import List, Dict, Any
from threading import RLock

from akaal.performance.event_bus.bus import PerformanceEventBus, PerformanceEvent


class AuditEvent(PerformanceEvent):
    """Event triggered for session audit updates."""
    def __init__(self, session_id: str, action: str, details: Dict[str, Any]) -> None:
        self.session_id = session_id
        self.action = action
        self.details = details


class OptimizationHistoryTracker:
    """Subscribes to audit events to maintain historical trace tables."""

    def __init__(self, event_bus: PerformanceEventBus) -> None:
        self._lock = RLock()
        self._event_bus = event_bus
        self._audit_log: List[Dict[str, Any]] = []

        # Subscribe to audit events
        self._event_bus.subscribe(AuditEvent, self.on_audit_event)

    def on_audit_event(self, event: AuditEvent) -> None:
        with self._lock:
            self._audit_log.append({
                "session_id": event.session_id,
                "action": event.action,
                "details": event.details
            })

    def get_audit_log(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._audit_log)
