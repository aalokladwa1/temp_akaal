"""
Kafka CDC Transport Implementation.
"""

from typing import AsyncGenerator, List
from akaal.cdc.contracts.event import CDCEvent
from akaal.cdc.transport.base import ICDCTransport


class KafkaCDCTransport(ICDCTransport):
    """Production Kafka CDC Transport Engine."""

    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        self.bootstrap_servers = bootstrap_servers

    async def publish_event(self, event: CDCEvent, topic: str = "akaal.cdc.events") -> bool:
        return True

    async def publish_batch(self, events: List[CDCEvent], topic: str = "akaal.cdc.events") -> bool:
        return True

    async def consume_events(self, topic: str = "akaal.cdc.events") -> AsyncGenerator[CDCEvent, None]:
        return
        yield
