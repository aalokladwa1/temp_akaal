"""
akaalEngine.discovery.models.environment
========================================
Server configuration, charsets, collations, timezones, and limits fact models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CharsetFacts:
    """Discovered character set encodings."""
    server_encoding: str = "UTF-8"
    client_encoding: Optional[str] = None
    national_charset: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_encoding": self.server_encoding,
            "client_encoding": self.client_encoding,
            "national_charset": self.national_charset,
        }


@dataclass(frozen=True)
class CollationFacts:
    """Discovered collation and sorting rules."""
    default_collation: str = "default"
    is_case_sensitive: bool = True
    is_accent_sensitive: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_collation": self.default_collation,
            "is_case_sensitive": self.is_case_sensitive,
            "is_accent_sensitive": self.is_accent_sensitive,
        }


@dataclass(frozen=True)
class TimezoneFacts:
    """Discovered database timezone and epoch settings."""
    database_timezone: str = "UTC"
    session_timezone: Optional[str] = None
    epoch_offset_seconds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_timezone": self.database_timezone,
            "session_timezone": self.session_timezone,
            "epoch_offset_seconds": self.epoch_offset_seconds,
        }


@dataclass(frozen=True)
class LimitsFacts:
    """Discovered connection, memory, and statement limits."""
    max_connections: Optional[int] = None
    active_connections: Optional[int] = None
    max_allowed_packet_bytes: Optional[int] = None
    statement_timeout_seconds: Optional[float] = None
    lock_timeout_seconds: Optional[float] = None
    block_size_bytes: int = 8192
    temp_tablespace_size_bytes: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_connections": self.max_connections,
            "active_connections": self.active_connections,
            "max_allowed_packet_bytes": self.max_allowed_packet_bytes,
            "statement_timeout_seconds": self.statement_timeout_seconds,
            "lock_timeout_seconds": self.lock_timeout_seconds,
            "block_size_bytes": self.block_size_bytes,
            "temp_tablespace_size_bytes": self.temp_tablespace_size_bytes,
        }


@dataclass(frozen=True)
class ConfigurationFacts:
    """Complete environment and engine configuration facts."""
    charset: CharsetFacts = field(default_factory=CharsetFacts)
    collation: CollationFacts = field(default_factory=CollationFacts)
    timezone: TimezoneFacts = field(default_factory=TimezoneFacts)
    limits: LimitsFacts = field(default_factory=LimitsFacts)
    installed_extensions: Tuple[str, ...] = field(default_factory=tuple)
    feature_flags: Mapping[str, bool] = field(default_factory=lambda: MappingProxyType({}))
    transaction_isolation_default: str = "READ COMMITTED"

    def __post_init__(self) -> None:
        if not isinstance(self.installed_extensions, tuple):
            object.__setattr__(self, "installed_extensions", tuple(self.installed_extensions))
        if not isinstance(self.feature_flags, MappingProxyType):
            object.__setattr__(self, "feature_flags", MappingProxyType(dict(self.feature_flags)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "charset": self.charset.to_dict(),
            "collation": self.collation.to_dict(),
            "timezone": self.timezone.to_dict(),
            "limits": self.limits.to_dict(),
            "installed_extensions": list(self.installed_extensions),
            "feature_flags": dict(self.feature_flags),
            "transaction_isolation_default": self.transaction_isolation_default,
        }


EnvironmentFacts = ConfigurationFacts

