"""
Akaal — Planner Event System
=============================
Immutable telemetry events and event bus for Planner Platform observability.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class PlannerEvent:
    """Immutable Planner telemetry event."""
    event_type: str
    correlation_id: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class PlannerEventBus:
    """Thread-safe event bus for broadcasting Planner telemetry events."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[PlannerEvent], None]] = []

    def subscribe(self, callback: Callable[[PlannerEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: PlannerEvent) -> None:
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception:
                pass
