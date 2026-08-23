"""
akaalEngine.discovery.spi.relational
===================================
Relational database discovery SPI extension contract.
Covers SQL tables, columns, PKs, FKs, constraints, indexes, programmables, partitions, and stats.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Optional, Sequence, Tuple

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.partitioning import PartitionFacts
from akaalEngine.discovery.models.programmables import ProgrammableInventory
from akaalEngine.discovery.models.statistics import TableSizeFacts
from akaalEngine.discovery.spi.strategy import BaseDiscoveryStrategy


class RelationalDiscoveryStrategy(BaseDiscoveryStrategy):
    """SPI interface for relational SQL database engines."""

    @abstractmethod
    def discover_programmables(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
    ) -> ProgrammableInventory:
        """Discovers stored procedures, functions, triggers, sequences, and UDTs."""
        ...

    @abstractmethod
    def discover_partitioning(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> PartitionFacts:
        """Discovers table partitioning strategies, key columns, and boundary expressions."""
        ...

    @abstractmethod
    def discover_table_statistics(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        context: DiscoveryContext,
    ) -> TableSizeFacts:
        """Discovers table rows, data bytes, index bytes, and LOB bytes."""
        ...

    def discover_dependency_graph(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
    ) -> Tuple[Tuple[str, str], ...]:
        """
        Discovers raw table-to-table foreign key dependency edges `(from_table, to_table)`.
        Default implementation returns an empty sequence if not overridden.
        """
        return tuple()
