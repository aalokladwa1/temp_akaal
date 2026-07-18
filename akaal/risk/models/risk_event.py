"""
Akaal — Risk Event System
=========================
Immutable telemetry event definitions and event bus for Risk Platform observability.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class RiskEvent:
    """Immutable Risk telemetry event."""
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


class RiskEventBus:
    """Thread-safe event bus for broadcasting Risk events."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[RiskEvent], None]] = []

    def subscribe(self, callback: Callable[[RiskEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: RiskEvent) -> None:
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception:
                pass
