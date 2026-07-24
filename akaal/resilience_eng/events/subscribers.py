"""Resilience Event Subscriber registry."""

from akaal.resilience_eng.events.event_bus import ResilienceEventBus, ResilienceEvent, ResilienceEventType
from typing import Callable


class ResilienceEventSubscriber:
    def __init__(self, event_bus: ResilienceEventBus):
        self._bus = event_bus

    def subscribe(self, event_type: ResilienceEventType, handler: Callable[[ResilienceEvent], None]) -> None:
        self._bus.subscribe(event_type, handler)
