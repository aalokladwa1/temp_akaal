"""
akaalEngine.discovery.spi.warehouse
==================================
Cloud data warehouse and lakehouse discovery SPI extension contract.
Covers datasets, tables, clustering keys, distribution styles, and external stages.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Mapping, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.spi.relational import RelationalDiscoveryStrategy


class WarehouseDiscoveryStrategy(RelationalDiscoveryStrategy):
    """SPI interface for analytical cloud warehouses (Snowflake, BigQuery, Redshift, Databricks)."""

    @abstractmethod
    def discover_warehouse_context(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> Mapping[str, Any]:
        """Discovers active compute warehouse, cluster size, or billing tier."""
        ...

    def discover_external_stages(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> Tuple[str, ...]:
        """Discovers external data stages or storage integrations."""
        return tuple()
