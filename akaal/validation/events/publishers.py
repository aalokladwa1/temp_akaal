"""Event publishers for publishing validation events."""

import logging
from typing import Any, Dict, Optional
from akaal.validation.events.event_bus import EventBus
from akaal.validation.events.events import ValidationEvent, EventType

logger = logging.getLogger("akaal.validation.publishers")


class EventPublisher:
    """Helper publisher wrapping EventBus calls."""

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._bus = event_bus or EventBus()

    @property
    def event_bus(self) -> EventBus:
        return self._bus

    async def publish_event(self, event_type: EventType, payload: Dict[str, Any], source: str = "akaal.validation") -> None:
        """Construct and publish a validation event."""
        event = ValidationEvent(event_type=event_type, payload=payload, source=source)
        await self._bus.publish(event)
