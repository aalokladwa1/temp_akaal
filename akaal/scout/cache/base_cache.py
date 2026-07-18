"""
Akaal — Base Discovery Cache Interface
======================================
Abstract cache contract for Scout discovery reports.
"""

import hashlib
from abc import ABC, abstractmethod
from typing import Optional
from akaal.core.models.project import ConnectionConfig
from akaal.scout.models.discovery_report import DiscoveryReport


class BaseDiscoveryCache(ABC):
    """Abstract discovery cache interface."""

    def generate_cache_key(self, config: ConnectionConfig, adapter_version: str = "1.0.0", fingerprint_version: str = "1.0.0") -> str:
        """Deterministic cache key formula: hash(engine:host:port:database:extra_schema:adapter_ver:fp_ver)."""
        schema_name = config.extra.get("schema", "default") if config.extra else "default"
        sys_type = config.system_type.value if hasattr(config.system_type, "value") else str(config.system_type)
        raw_key = f"{sys_type}:{config.host}:{config.port}:{config.database_name}:{schema_name}:{adapter_version}:{fingerprint_version}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @abstractmethod
    def get(self, key: str) -> Optional[DiscoveryReport]:
        """Retrieve cached DiscoveryReport by key."""

    @abstractmethod
    def set(self, key: str, report: DiscoveryReport, ttl_seconds: Optional[int] = None) -> None:
        """Store DiscoveryReport in cache with optional TTL."""

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Invalidate key in cache."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries in cache."""
