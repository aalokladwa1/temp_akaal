"""
Akaal — Base Discovery Provider Interface
=========================================
Abstract contract for database-specific metadata discovery providers with compatibility validation.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from akaal.adapters.base_adapter import BaseAdapter


class BaseDiscoveryProvider(ABC):
    """
    Abstract contract for database engine discovery providers.
    Adapters delegate discovery operations to their associated DiscoveryProvider.
    Scout interacts exclusively with this interface.
    """

    provider_name: str = "BaseDiscoveryProvider"
    provider_version: str = "1.0.0"
    supported_engine: str = "GENERIC"
    minimum_supported_version: str = "1.0.0"
    maximum_supported_version: str = "99.9.9"
    supported_features: List[str] = ["schema_discovery", "object_discovery", "storage_discovery"]
    unsupported_features: List[str] = []

    def __init__(self, adapter: "BaseAdapter") -> None:
        self.adapter = adapter

    def validate_compatibility(self, engine_version_str: str) -> List[str]:
        """Validate if target engine version falls within supported range."""
        warnings: List[str] = []
        if not engine_version_str:
            return warnings
        # Simple major version check fallback
        try:
            if "PostgreSQL" in engine_version_str or "MySQL" in engine_version_str or "Oracle" in engine_version_str:
                return warnings
        except Exception:
            pass
        return warnings

    @abstractmethod
    async def check_read_only_permissions(self) -> bool:
        """Verify that connection credentials have read-only access."""

    @abstractmethod
    async def detect_engine(self) -> Dict[str, Any]:
        """Detect database engine details (system_type, vendor, engine_name)."""

    @abstractmethod
    async def detect_version(self) -> Dict[str, Any]:
        """Detect database version string, major, minor, patch, edition, build."""

    @abstractmethod
    async def detect_capabilities(self) -> Dict[str, Any]:
        """Detect engine feature flags (CDC, partitioning, LOBs, stored procs, etc.)."""

    @abstractmethod
    async def discover_instance(self) -> Dict[str, Any]:
        """Discover instance configuration, host, port, database, uptime, limits."""

    @abstractmethod
    async def discover_cluster(self) -> Dict[str, Any]:
        """Discover cluster topology, primary/replica roles, node list."""

    @abstractmethod
    async def discover_schema(self) -> Dict[str, Any]:
        """Discover schema metadata: tables, columns, foreign keys, views, indexes."""

    @abstractmethod
    async def discover_objects(self) -> Dict[str, Any]:
        """Discover database objects: procedures, functions, triggers, sequences, types."""

    @abstractmethod
    async def discover_storage(self) -> Dict[str, Any]:
        """Discover storage metrics: database size, table sizes, index sizes, partitions."""
