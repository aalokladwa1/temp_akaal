"""
AKAAL Enterprise Intelligence Platform — Events Subsystem
==========================================================
Immutable telemetry event classes and thread-safe passive event bus for Platform 2.
"""

from dataclasses import dataclass, field
import threading
import time
from typing import Any, Callable, Dict, List, Type


@dataclass(frozen=True)
class IntelligenceEvent:
    """Base class for all Platform 2 telemetry events."""
    event_id: str
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlatformStartedEvent(IntelligenceEvent):
    """Event emitted when Platform 2 pipeline begins execution."""
    advisory_model_id: str = ""


@dataclass(frozen=True)
class ValidationCompletedEvent(IntelligenceEvent):
    """Event emitted when model validation completes."""
    is_valid: bool = True


@dataclass(frozen=True)
class PlatformCompletedEvent(IntelligenceEvent):
    """Event emitted when Platform 2 pipeline finishes execution successfully."""
    intelligence_model_id: str = ""
    checksum: str = ""


@dataclass(frozen=True)
class ValidationFailedEvent(IntelligenceEvent):
    """Event emitted when model validation fails."""
    error_message: str = ""


class EnterpriseIntelligenceEventBus:
    """
    Thread-safe passive telemetry event bus.
    Subscribers receive read-only notifications; handlers cannot mutate pipeline state.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[Type[IntelligenceEvent], List[Callable[[IntelligenceEvent], None]]] = {}
        self._published_events: List[IntelligenceEvent] = []
        self._lock: threading.Lock = threading.Lock()

    def subscribe(
        self,
        event_type: Type[IntelligenceEvent],
        handler: Callable[[IntelligenceEvent], None],
    ) -> None:
        """Subscribes a passive callback handler to an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)

    def publish(self, event: IntelligenceEvent) -> None:
        """Publishes a telemetry event to registered subscribers."""
        with self._lock:
            self._published_events.append(event)
            handlers = list(self._subscribers.get(type(event), []))
            # Also notify wildcard subscribers for base IntelligenceEvent
            if type(event) is not IntelligenceEvent:
                handlers.extend(self._subscribers.get(IntelligenceEvent, []))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                # Event subscriber exceptions MUST be swallowed to guarantee non-blocking telemetry
                pass

    def get_published_events(self) -> List[IntelligenceEvent]:
        """Returns a snapshot copy of all published events."""
        with self._lock:
            return list(self._published_events)

    def clear(self) -> None:
        """Clears all subscribers and published events."""
        with self._lock:
            self._subscribers.clear()
            self._published_events.clear()
