"""
akaalEngine.discovery.models.identity
=====================================
Physical endpoint identity and server version fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ServerVersion:
    """Discovered server version details."""
    raw_version_string: str
    major: int = 0
    minor: int = 0
    patch: int = 0
    build_number: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_version_string": self.raw_version_string,
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "build_number": self.build_number,
        }


@dataclass(frozen=True)
class EngineEdition:
    """Discovered engine edition details."""
    edition_name: str
    is_enterprise: bool = False
    is_cloud_managed: bool = False
    details: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.details, MappingProxyType):
            object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "edition_name": self.edition_name,
            "is_enterprise": self.is_enterprise,
            "is_cloud_managed": self.is_cloud_managed,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class DiscoveredEndpointIdentity:
    """
    Authoritative physical facts about the connected endpoint's engine, version, and instance.
    """
    provider_id: str
    vendor_name: str
    engine_name: str
    system_type: str
    version: ServerVersion
    edition: EngineEdition
    instance_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    uptime_seconds: Optional[int] = None
    extra_properties: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.extra_properties, MappingProxyType):
            object.__setattr__(self, "extra_properties", MappingProxyType(dict(self.extra_properties)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "vendor_name": self.vendor_name,
            "engine_name": self.engine_name,
            "system_type": self.system_type,
            "version": self.version.to_dict(),
            "edition": self.edition.to_dict(),
            "instance_name": self.instance_name,
            "host": self.host,
            "port": self.port,
            "database_name": self.database_name,
            "uptime_seconds": self.uptime_seconds,
            "extra_properties": dict(self.extra_properties),
        }
