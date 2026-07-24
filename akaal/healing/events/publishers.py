"""HealingEventPublisher for publishing self-healing events."""

from typing import Dict, Any, Optional
from akaal.healing.events.events import HealingEvent, HealingEventType
from akaal.healing.events.event_bus import HealingEventBus


class HealingEventPublisher:
    """Helper publisher wrapping HealingEventBus."""

    def __init__(self, event_bus: Optional[HealingEventBus] = None):
        self.bus = event_bus or HealingEventBus()

    async def publish(self, event_type: HealingEventType, payload: Dict[str, Any]) -> None:
        event = HealingEvent(event_type=event_type, payload=payload)
        await self.bus.publish(event)
