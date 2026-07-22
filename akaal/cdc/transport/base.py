"""
Abstract Transport Interface for CDC Events.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List
from akaal.cdc.contracts.event import CDCEvent


class ICDCTransport(ABC):
    """Abstract Interface for Transporting CDC Change Events."""

    @abstractmethod
    async def publish_event(self, event: CDCEvent, topic: str = "akaal.cdc.events") -> bool:
        """Publish single CDC event to transport broker."""
        pass

    @abstractmethod
    async def publish_batch(self, events: List[CDCEvent], topic: str = "akaal.cdc.events") -> bool:
        """Publish batch of CDC events to transport broker."""
        pass

    @abstractmethod
    async def consume_events(self, topic: str = "akaal.cdc.events") -> AsyncGenerator[CDCEvent, None]:
        """Consume stream of CDC events from transport broker."""
        pass
