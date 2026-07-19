"""
AKAAL Enterprise Intelligence Platform — Version Info Model
============================================================
Represents schema version information for Platform 2 Enterprise Intelligence models.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class EnterpriseIntelligenceVersionInfo:
    """
    Immutable version information detailing semantic schema versioning.
    """

    schema_version: str = "1.0.0"
    platform_version: str = "1.0.0"
    compatibility_flags: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.compatibility_flags, MappingProxyType):
            object.__setattr__(
                self,
                "compatibility_flags",
                MappingProxyType(dict(self.compatibility_flags) if self.compatibility_flags else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "schema_version": self.schema_version,
            "platform_version": self.platform_version,
            "compatibility_flags": dict(self.compatibility_flags),
        }
