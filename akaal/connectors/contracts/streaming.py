"""
AKAAL Stream & Event Platform Capability Extension Contract (P4.1).
====================================================================
Defines event and message stream platform capability extension interfaces:
- Apache Kafka, Confluent, Amazon MSK, Amazon Kinesis, Azure Event Hubs, Google Pub/Sub
- Topic and partition discovery
- Offset and sequence tracking
- Batch event publishing and consumption
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IStreamingCapability(ABC):
    """Extension contract for streaming & event platforms (Kafka, Kinesis, Event Hubs, Pub/Sub)."""

    @abstractmethod
    async def discover_topics(self) -> List[str]:
        """Discovers available topics / streams."""
        pass

    @abstractmethod
    async def discover_partitions(self, topic_name: str) -> List[Dict[str, Any]]:
        """Discovers topic partitions / shards and watermark offsets."""
        pass

    @abstractmethod
    async def publish_events_batch(
        self,
        topic_name: str,
        events: List[Dict[str, Any]],
        partition_key_field: Optional[str] = None,
    ) -> int:
        """Publishes batch of events to topic. Returns count of published events."""
        pass

    @abstractmethod
    async def consume_events_batch(
        self,
        topic_name: str,
        partition_id: int,
        start_offset: int,
        max_messages: int = 100,
    ) -> List[Dict[str, Any]]:
        """Consumes batch of events from partition offset."""
        pass
