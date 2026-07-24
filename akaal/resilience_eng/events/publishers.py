"""ResilienceEventPublisher: Publishes typed resilience events to the event bus."""

from akaal.resilience_eng.events.event_bus import ResilienceEventBus, ResilienceEvent, ResilienceEventType
from typing import Dict, Any


class ResilienceEventPublisher:
    def __init__(self, event_bus: ResilienceEventBus):
        self._bus = event_bus

    def publish(self, event_type: ResilienceEventType, experiment_id: str, payload: Dict[str, Any] = None) -> ResilienceEvent:
        event = ResilienceEvent(event_type=event_type, experiment_id=experiment_id, payload=payload or {})
        self._bus.publish(event)
        return event
