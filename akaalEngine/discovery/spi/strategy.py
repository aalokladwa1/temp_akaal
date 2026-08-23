"""
akaalEngine.discovery.spi.strategy
=================================
Base Discovery Strategy SPI contract.
Integrates with Authority #2 Extensions for strategy resolution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Sequence

from akaalEngine.connection.models.endpoint import EndpointSpec
from akaalEngine.connection.routing.resolver import ResolvedRoute
from akaalEngine.discovery.models.cdc import CDCPrerequisiteSnapshot
from akaalEngine.discovery.models.context import DiscoveryContext
from akaalEngine.discovery.models.environment import ConfigurationFacts
from akaalEngine.discovery.models.identity import DiscoveredEndpointIdentity
from akaalEngine.discovery.models.inventory import NamespaceInventory, ObjectInventoryPage, TableFacts, ViewFacts
from akaalEngine.discovery.models.partitioning import PartitionFacts
from akaalEngine.discovery.models.permissions import PermissionAssessment, ThreeStatePermission
from akaalEngine.discovery.models.sampling import SampledRecordSet
from akaalEngine.discovery.models.statistics import TableSizeFacts
from akaalEngine.discovery.models.structure import ObjectStructureFacts
from akaalEngine.discovery.models.topology import TopologySnapshot


class BaseDiscoveryStrategy(ABC):
    """
    Abstract SPI protocol for provider-specific physical endpoint discovery.
    Concrete strategies are registered via Extensions Authority and leased via Connection Authority.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """The canonical ProviderId string for this strategy."""
        ...

    @abstractmethod
    def discover_endpoint_identity(
        self,
        connection: Any,
        spec: EndpointSpec,
        route: Optional[ResolvedRoute] = None,
    ) -> DiscoveredEndpointIdentity:
        """Discovers native engine identity, version, edition, and instance parameters."""
        ...

    @abstractmethod
    def discover_namespaces(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> NamespaceInventory:
        """Discovers catalogs, schemas, keyspaces, buckets, or topic namespaces."""
        ...

    @abstractmethod
    def discover_objects_page(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        context: DiscoveryContext,
        cursor: Optional[str] = None,
        page_size: int = 500,
    ) -> ObjectInventoryPage:
        """Discovers a paginated slice of tables, views, or collections within a schema."""
        ...

    @abstractmethod
    def discover_object_structure(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_name: str,
        context: DiscoveryContext,
    ) -> ObjectStructureFacts:
        """Discovers detailed column, constraint, and index structure for a single table/object."""
        ...

    def discover_objects_structure_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, ObjectStructureFacts]:
        """
        Bulk discovers structure facts for a page/batch of objects in bounded query count.
        Default implementation falls back to per-object discover_object_structure.
        """
        results: dict[str, ObjectStructureFacts] = {}
        for name in object_names:
            results[name] = self.discover_object_structure(
                connection, spec, schema_name, name, context
            )
        return results

    def discover_table_statistics_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, TableSizeFacts]:
        """
        Bulk discovers size and row count facts for a batch of objects.
        Default implementation calls discover_table_statistics per object if available.
        """
        results: dict[str, TableSizeFacts] = {}
        for name in object_names:
            if hasattr(self, "discover_table_statistics"):
                results[name] = getattr(self, "discover_table_statistics")(
                    connection, spec, schema_name, name, context
                )
        return results

    def discover_partitions_bulk(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        object_names: Sequence[str],
        context: DiscoveryContext,
    ) -> Mapping[str, PartitionFacts]:
        """
        Bulk discovers partition facts for a batch of objects.
        Default implementation calls discover_partitions per object if available.
        """
        results: dict[str, PartitionFacts] = {}
        for name in object_names:
            if hasattr(self, "discover_partitions"):
                results[name] = getattr(self, "discover_partitions")(
                    connection, spec, schema_name, name, context
                )
        return results

    @abstractmethod
    def check_read_only_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> ThreeStatePermission:
        """Verifies whether the current connection session is strictly read-only."""
        ...

    @abstractmethod
    def discover_permissions(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> PermissionAssessment:
        """Evaluates 3-state authorization truth across required catalog and table permissions."""
        ...

    @abstractmethod
    def discover_environment(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> ConfigurationFacts:
        """Discovers server character sets, collations, timezones, and connection limits."""
        ...

    @abstractmethod
    def discover_topology(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> TopologySnapshot:
        """Discovers physical cluster nodes, replication roles, and standby replication lag."""
        ...

    @abstractmethod
    def discover_cdc_prerequisites(
        self,
        connection: Any,
        spec: EndpointSpec,
        context: DiscoveryContext,
    ) -> CDCPrerequisiteSnapshot:
        """Discovers CDC log mining settings, replication slots, and starting commit coordinates."""
        ...

    @abstractmethod
    def sample_data(
        self,
        connection: Any,
        spec: EndpointSpec,
        schema_name: str,
        table_name: str,
        limit: int = 100,
        timeout_seconds: float = 3.0,
    ) -> SampledRecordSet:
        """Executes bounded, low-impact, cancelable preview sampling on an object."""
        ...

    def get_schema_change_marker(
        self,
        connection: Any,
        spec: EndpointSpec,
    ) -> Optional[str]:
        """
        Returns a lightweight transaction or catalog generation marker for detecting DDL mutation.
        Default implementation returns None if provider cannot expose catalog change tokens.
        """
        return None

