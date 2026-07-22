"""
In-Memory CDC Transport Implementation for Testing and Local Setup.
"""

from typing import AsyncGenerator, List, Dict
from akaal.cdc.contracts.event import CDCEvent
from akaal.cdc.transport.base import ICDCTransport


class InMemoryCDCTransport(ICDCTransport):
    """In-Memory CDC Transport Engine."""

    def __init__(self) -> None:
        self.published_topics: Dict[str, List[CDCEvent]] = {}

    async def publish_event(self, event: CDCEvent, topic: str = "akaal.cdc.events") -> bool:
        if topic not in self.published_topics:
            self.published_topics[topic] = []
        self.published_topics[topic].append(event)
        return True

    async def publish_batch(self, events: List[CDCEvent], topic: str = "akaal.cdc.events") -> bool:
        if topic not in self.published_topics:
            self.published_topics[topic] = []
        self.published_topics[topic].extend(events)
        return True

    async def consume_events(self, topic: str = "akaal.cdc.events") -> AsyncGenerator[CDCEvent, None]:
        events = self.published_topics.get(topic, [])
        for evt in events:
            yield evt
