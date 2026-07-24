"""HealingEventBus, HealingEventPublisher, HealingEventSubscriber."""

import inspect
import asyncio
import logging
from typing import Callable, Dict, List, Coroutine, Any
from akaal.healing.events.events import HealingEvent, HealingEventType

logger = logging.getLogger("akaal.healing.events")


class HealingEventBus:
    """Async event bus for self-healing lifecycle events."""

    def __init__(self):
        self._subscribers: Dict[HealingEventType, List[Callable[[HealingEvent], Coroutine[Any, Any, None]]]] = {}

    def subscribe(self, event_type: HealingEventType, callback: Callable[[HealingEvent], Coroutine[Any, Any, None]]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[HealingEvent], Coroutine[Any, Any, None]]) -> None:
        for et in HealingEventType:
            self.subscribe(et, callback)

    async def publish(self, event: HealingEvent) -> None:
        callbacks = self._subscribers.get(event.event_type, [])
        if not callbacks:
            return

        tasks = []
        for cb in callbacks:
            try:
                if inspect.iscoroutinefunction(cb):
                    tasks.append(cb(event))
                else:
                    cb(event)
            except Exception as exc:
                logger.error(f"Error handling healing event {event.event_type}: {exc}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


class HealingEventPublisher:
    """Helper publisher wrapping HealingEventBus."""

    def __init__(self, event_bus: Optional[HealingEventBus] = None):
        self.bus = event_bus or HealingEventBus()

    async def publish(self, event_type: HealingEventType, payload: Dict[str, Any]) -> None:
        event = HealingEvent(event_type=event_type, payload=payload)
        await self.bus.publish(event)


class HealingEventSubscriber:
    """Base subscriber."""
    pass


class HealingMetricsSubscriber:
    """Subscribes and tracks metrics for healing events."""

    def __init__(self):
        self.event_counts: Dict[str, int] = {}

    async def on_event(self, event: HealingEvent) -> None:
        key = event.event_type.value
        self.event_counts[key] = self.event_counts.get(key, 0) + 1
