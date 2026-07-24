"""Async EventBus supporting decoupling, multiple subscribers, and future streaming/websockets."""

import inspect
import asyncio
import logging
from typing import Callable, Dict, List, Coroutine, Any
from akaal.validation.events.events import ValidationEvent, EventType

logger = logging.getLogger("akaal.validation.event_bus")


class EventBus:
    """Decoupled async event bus."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[ValidationEvent], Coroutine[Any, Any, None]]]] = {}

    def subscribe(
        self, event_type: EventType, callback: Callable[[ValidationEvent], Coroutine[Any, Any, None]]
    ) -> None:
        """Register an async callback for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[ValidationEvent], Coroutine[Any, Any, None]]) -> None:
        """Subscribe to all event types."""
        for et in EventType:
            self.subscribe(et, callback)

    async def publish(self, event: ValidationEvent) -> None:
        """Publish an event asynchronously to all registered subscribers."""
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
                logger.error(f"Error handling event {event.event_type}: {exc}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
