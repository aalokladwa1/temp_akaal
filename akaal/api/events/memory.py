"""
In-Memory Event Publisher Implementation.
"""

from typing import List
from akaal.api.events.models import DomainEvent
from akaal.api.events.publisher import IEventPublisher


class InMemoryEventPublisher(IEventPublisher):
    """In-Memory Event Publisher for Testing & Local Profile."""

    def __init__(self) -> None:
        self.published_events: List[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> bool:
        self.published_events.append(event)
        return True
