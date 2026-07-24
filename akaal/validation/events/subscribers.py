"""Event subscribers (Logging, Metrics, Audit, Notifications)."""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from akaal.validation.events.events import ValidationEvent

logger = logging.getLogger("akaal.validation.subscribers")


class EventSubscriber(ABC):
    """Abstract base subscriber."""

    @abstractmethod
    async def on_event(self, event: ValidationEvent) -> None:
        """Handle incoming event."""
        pass


class LoggingSubscriber(EventSubscriber):
    """Subscriber that logs all validation events."""

    async def on_event(self, event: ValidationEvent) -> None:
        logger.info(f"[EVENT] [{event.event_type.value}] ID={event.event_id} Payload={event.payload}")


class MetricsSubscriber(EventSubscriber):
    """Subscriber that collects in-memory event metrics."""

    def __init__(self):
        self.event_counts: Dict[str, int] = {}
        self.history: List[ValidationEvent] = []

    async def on_event(self, event: ValidationEvent) -> None:
        key = event.event_type.value
        self.event_counts[key] = self.event_counts.get(key, 0) + 1
        self.history.append(event)
