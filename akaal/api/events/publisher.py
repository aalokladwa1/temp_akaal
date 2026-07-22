"""
Abstract Event Publisher Interface.
"""

from abc import ABC, abstractmethod
from akaal.api.events.models import DomainEvent


class IEventPublisher(ABC):
    """Abstract Interface for Enterprise Event Publishers."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> bool:
        """Publish a domain event to message broker."""
        pass
