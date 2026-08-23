"""
akaalEngine.discovery.spi.streaming
===================================
Streaming message bus discovery SPI extension contract.
Covers Kafka, Kinesis, Event Hubs, and Google Cloud Pub/Sub.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy


class StreamingDiscoveryStrategy(BaseDiscoveryStrategy):
    """SPI interface for streaming and message broker endpoints."""

    @abstractmethod
    def discover_topic_retention_policy(
        self,
        connection: Any,
        spec: EndpointSpec,
        topic_name: str,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        """Discovers topic retention duration, bytes quota, and cleanup compaction policies."""
        ...
