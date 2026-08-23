"""
akaalEngine.connection.catalog.provider_catalog
==============================================
Thread-safe, deterministic Provider Catalog for Connection Authority.
Consumes provider strategy implementations and exposes registration seam for future Authority #2 (Extensions).
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Type

from akaalEngine.connection.models.capability import StaticCapabilityManifest
from akaalEngine.connection.models.errors import (
    ConfigurationError,
    ConnectionFailure,
    FailureCategory,
)
from akaalEngine.connection.providers.base import BaseProviderStrategy

logger = logging.getLogger("akaalEngine.connection.catalog")


class ProviderCatalog:
    """
    Central Authoritative Catalog for all database, storage, and streaming providers in akaalEngine.
    Thread-safe, deterministic, and fail-closed.
    """

    _INSTANCE: Optional["ProviderCatalog"] = None
    _LOCK = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._providers: Dict[str, BaseProviderStrategy] = {}
        self._manifests: Dict[str, StaticCapabilityManifest] = {}
        self._generation: int = 1

    @classmethod
    def get_instance(cls) -> "ProviderCatalog":
        """Singleton accessor with thread-safe double-checked locking."""
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    catalog = cls()
                    catalog.bootstrap_builtin_providers()
                    cls._INSTANCE = catalog
        return cls._INSTANCE

    def get_catalog_generation(self) -> int:
        """Returns the current catalog strategy generation counter."""
        with self._lock:
            return self._generation

    def _normalize_id(self, provider_id: Optional[str]) -> str:
        if not provider_id or not str(provider_id).strip():
            raise ValueError("Provider ID must be a non-empty string.")
        return str(provider_id).strip().lower()

    def register_provider(
        self,
        strategy: BaseProviderStrategy,
        allow_override: bool = False,
    ) -> None:
        """
        Registers a provider strategy with authoritative manifest.
        Seam used by built-in providers and future Extensions Authority.
        """
        with self._lock:
            pid = self._normalize_id(strategy.PROVIDER_ID)
            is_replacement = pid in self._providers
            if not allow_override and is_replacement:
                raise ValueError(f"Provider '{pid}' is already registered. Set allow_override=True to replace.")

            manifest = strategy.get_static_manifest()
            self._providers[pid] = strategy
            self._manifests[pid] = manifest
            if is_replacement:
                self._generation += 1
                # Trigger invalidation for pools created with previous strategy generation
                try:
                    from akaalEngine.connection.pooling.invalidation import default_invalidation_coordinator
                    default_invalidation_coordinator.broadcast_invalidation(
                        fingerprint=None,
                        reason=f"Provider strategy '{pid}' replaced (generation {self._generation}).",
                    )
                except Exception:
                    pass
            logger.info(f"[ProviderCatalog] Registered provider '{pid}' ({manifest.vendor_name}, family={manifest.family}, generation={self._generation}).")

    def unregister_provider(self, provider_id: str) -> bool:
        """Unregisters a provider strategy."""
        with self._lock:
            try:
                pid = self._normalize_id(provider_id)
                removed = bool(self._providers.pop(pid, None))
                self._manifests.pop(pid, None)
                if removed:
                    self._generation += 1
                    try:
                        from akaalEngine.connection.pooling.invalidation import default_invalidation_coordinator
                        default_invalidation_coordinator.broadcast_invalidation(
                            fingerprint=None,
                            reason=f"Provider strategy '{pid}' unregistered (generation {self._generation}).",
                        )
                    except Exception:
                        pass
                    logger.info(f"[ProviderCatalog] Unregistered provider '{pid}'.")
                return removed
            except ValueError:
                return False

    def is_provider_registered(self, provider_id: str) -> bool:
        with self._lock:
            try:
                pid = self._normalize_id(provider_id)
                return pid in self._providers
            except ValueError:
                return False

    def get_strategy(self, provider_id: str) -> BaseProviderStrategy:
        """
        Retrieves the registered BaseProviderStrategy for a given provider ID.
        Raises ConfigurationError with fail-closed ConnectionFailure if not found.
        """
        with self._lock:
            pid = self._normalize_id(provider_id)
            if pid not in self._providers:
                msg = f"Unknown or unregistered provider: '{provider_id}'. Available providers: {sorted(self._providers.keys())}"
                failure = ConnectionFailure(
                    error_code="PROVIDER_NOT_REGISTERED",
                    category=FailureCategory.INVALID_CONFIGURATION,
                    message=msg,
                    retryable=False,
                    provider_id=pid,
                    remediation="Verify connector name spelling or ensure the appropriate provider strategy is registered.",
                )
                raise ConfigurationError(failure)
            return self._providers[pid]

    def describe_provider(self, provider_id: str) -> StaticCapabilityManifest:
        """Returns the authoritative static capability manifest for a provider."""
        with self._lock:
            pid = self._normalize_id(provider_id)
            strategy = self.get_strategy(pid)
            return strategy.get_static_manifest()

    def list_providers(self) -> List[str]:
        """Returns sorted list of all registered provider IDs."""
        with self._lock:
            return sorted(self._providers.keys())

    def bootstrap_builtin_providers(self) -> None:
        """Bootstraps all built-in relational, warehouse, nosql, streaming, and storage providers."""
        with self._lock:
            from akaalEngine.connection.providers.relational import (
                SQLiteProviderStrategy,
                PostgreSQLProviderStrategy,
                MySQLProviderStrategy,
                MariaDBProviderStrategy,
                OracleProviderStrategy,
                MSSQLProviderStrategy,
                IBMDb2ProviderStrategy,
            )
            from akaalEngine.connection.providers.warehouse import (
                SnowflakeProviderStrategy,
                BigQueryProviderStrategy,
                RedshiftProviderStrategy,
                DatabricksProviderStrategy,
            )
            from akaalEngine.connection.providers.nosql import (
                MongoDBProviderStrategy,
                CassandraProviderStrategy,
                ScyllaDBProviderStrategy,
                Neo4jProviderStrategy,
                RedisProviderStrategy,
                KeyDBProviderStrategy,
                ElasticsearchProviderStrategy,
                OpenSearchProviderStrategy,
            )
            from akaalEngine.connection.providers.streaming import (
                KafkaProviderStrategy,
                KinesisProviderStrategy,
                EventHubsProviderStrategy,
                PubSubProviderStrategy,
            )
            from akaalEngine.connection.providers.storage import (
                S3ProviderStrategy,
                GCSProviderStrategy,
                AzureBlobProviderStrategy,
                MinIOProviderStrategy,
                HDFSProviderStrategy,
            )

            strategies: list[BaseProviderStrategy] = [
                # Relational
                SQLiteProviderStrategy(),
                PostgreSQLProviderStrategy(),
                MySQLProviderStrategy(),
                MariaDBProviderStrategy(),
                OracleProviderStrategy(),
                MSSQLProviderStrategy(),
                IBMDb2ProviderStrategy(),
                # Warehouse
                SnowflakeProviderStrategy(),
                BigQueryProviderStrategy(),
                RedshiftProviderStrategy(),
                DatabricksProviderStrategy(),
                # NoSQL
                MongoDBProviderStrategy(),
                CassandraProviderStrategy(),
                ScyllaDBProviderStrategy(),
                Neo4jProviderStrategy(),
                RedisProviderStrategy(),
                KeyDBProviderStrategy(),
                ElasticsearchProviderStrategy(),
                OpenSearchProviderStrategy(),
                # Streaming
                KafkaProviderStrategy(),
                KinesisProviderStrategy(),
                EventHubsProviderStrategy(),
                PubSubProviderStrategy(),
                # Storage
                S3ProviderStrategy(),
                GCSProviderStrategy(),
                AzureBlobProviderStrategy(),
                MinIOProviderStrategy(),
                HDFSProviderStrategy(),
            ]

            for s in strategies:
                self.register_provider(s, allow_override=True)


# Global catalog instance accessor
default_provider_catalog = ProviderCatalog.get_instance()
