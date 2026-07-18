"""
Akaal — Discovery Provider Registry
===================================
Central registry for resolving database DiscoveryProvider implementations by SystemType.
"""

import threading
from typing import Any, Dict, List, Optional, Type
from akaal.core.models.enums import SystemType
from akaal.adapters.providers.base_provider import BaseDiscoveryProvider
from akaal.adapters.providers.generic_provider import GenericDiscoveryProvider
from akaal.adapters.providers.postgres_provider import PostgresDiscoveryProvider
from akaal.adapters.providers.mysql_provider import MySQLDiscoveryProvider
from akaal.adapters.providers.oracle_provider import OracleDiscoveryProvider


class DiscoveryProviderRegistry:
    """Registry for database engine metadata discovery providers."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._registry: Dict[SystemType, Type[BaseDiscoveryProvider]] = {}
        self._versions: Dict[SystemType, str] = {}
        self._capabilities: Dict[SystemType, Dict[str, Any]] = {}
        self._bootstrap_default_providers()

    def _bootstrap_default_providers(self) -> None:
        self.register(SystemType.POSTGRESQL, PostgresDiscoveryProvider, "1.0.0", {"cdc": True, "partitioning": True})
        self.register(SystemType.MYSQL, MySQLDiscoveryProvider, "1.0.0", {"cdc": True, "partitioning": True})
        self.register(SystemType.ORACLE, OracleDiscoveryProvider, "1.0.0", {"cdc": True, "partitioning": True, "lob_streaming": True})

    def register(
        self,
        system_type: SystemType,
        provider_cls: Type[BaseDiscoveryProvider],
        version: str = "1.0.0",
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            self._registry[system_type] = provider_cls
            self._versions[system_type] = version
            self._capabilities[system_type] = capabilities or {}

    def resolve(self, system_type: SystemType) -> Type[BaseDiscoveryProvider]:
        with self._lock:
            if system_type in self._registry:
                return self._registry[system_type]
            return GenericDiscoveryProvider

    def validate_provider_compatibility(self, system_type: SystemType, engine_version_str: str) -> List[str]:
        with self._lock:
            provider_cls = self.resolve(system_type)
            dummy_instance = provider_cls(None)
            return dummy_instance.validate_compatibility(engine_version_str)

    def supports(self, system_type: SystemType) -> bool:
        with self._lock:
            return system_type in self._registry

    def list_plugins(self) -> List[str]:
        with self._lock:
            return [st.value if hasattr(st, "value") else str(st) for st in self._registry.keys()]

    def plugin_version(self, system_type: SystemType) -> str:
        with self._lock:
            return self._versions.get(system_type, "1.0.0")

    def plugin_capabilities(self, system_type: SystemType) -> Dict[str, Any]:
        with self._lock:
            return self._capabilities.get(system_type, {})
