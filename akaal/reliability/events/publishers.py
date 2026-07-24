"""ReliabilityEventPublisher re-export."""
from akaal.reliability.events.events import ReliabilityEvent, ReliabilityEventType
from akaal.reliability.events.event_bus import ReliabilityEventBus


class ReliabilityEventPublisher:
    """Helper publisher wrapping ReliabilityEventBus."""

    def __init__(self, bus: ReliabilityEventBus):
        self.bus = bus

    async def publish_failure(self, component: str, error: str):
        await self.bus.publish(ReliabilityEvent(ReliabilityEventType.FAILURE_DETECTED, {"component": component, "error": error}))
