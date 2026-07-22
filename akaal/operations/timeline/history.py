"""
Operational Timeline History.
Chronological append-only history of administrative actions, events, and health changes.
"""

from typing import Dict, List, Any
from threading import RLock
import time


class OperationalTimeline:
    """Chronological event timeline store."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._timeline: List[Dict[str, Any]] = []

    def record_event(self, actor: str, action: str, source_platform: str, correlation_id: str, severity: str = "INFO", details: Dict[str, Any] = None) -> None:
        with self._lock:
            self._timeline.append({
                "timestamp": time.time(),
                "actor": actor,
                "action": action,
                "source_platform": source_platform,
                "correlation_id": correlation_id,
                "severity": severity,
                "details": details or {}
            })

    def get_timeline(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._timeline)
