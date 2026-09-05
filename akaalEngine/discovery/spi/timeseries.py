"""
akaalEngine.discovery.spi.timeseries
======================================
Time-series database discovery SPI extension contract (P7A Campaign B).
Covers InfluxDB and future time-series-native providers (measurement/tag/field model,
retention policies -- genuinely distinct from relational, NoSQL document, and streaming
discovery contracts).
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Mapping

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy


class TimeSeriesDiscoveryStrategy(BaseDiscoveryStrategy):
    """SPI interface for time-series-native databases (measurement/tag/field model)."""

    @abstractmethod
    def discover_retention_policy(
        self,
        connection: Any,
        spec: EndpointSpec,
        bucket_name: str,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        """Discovers the retention duration and shard-group configuration for a bucket/measurement."""
        ...
