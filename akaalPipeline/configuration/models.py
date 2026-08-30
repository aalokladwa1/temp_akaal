"""akaalPipeline.configuration.models
=====================================
Configuration scopes, layers, effective configuration, and provenance models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ConfigurationScope(str, Enum):
    PLATFORM = "platform"
    DEFAULT = "default"
    ORGANIZATION = "organization"
    TEMPLATE = "template"
    WORKSPACE = "workspace"
    PROJECT = "project"
    MIGRATION = "migration"
    PLAN = "plan"
    INITIALIZATION = "initialization"


@dataclass(frozen=True)
class ConfigurationLayer:
    scope: ConfigurationScope
    settings: Mapping[str, Any]

    def __post_init__(self) -> None:
        from akaalPipeline.contracts.serialization import deep_freeze
        object.__setattr__(self, "settings", deep_freeze(self.settings))


@dataclass(frozen=True)
class EffectiveConfiguration:
    resolved_values: Mapping[str, Any]
    provenance: Mapping[str, str]  # key -> scope string
    overrides: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from akaalPipeline.contracts.serialization import deep_freeze
        object.__setattr__(self, "resolved_values", deep_freeze(self.resolved_values))
        object.__setattr__(self, "provenance", deep_freeze(self.provenance))
        object.__setattr__(self, "overrides", deep_freeze(self.overrides))

    def get(self, key: str, default: Any = None) -> Any:
        return self.resolved_values.get(key, default)

    @property
    def fingerprint(self) -> str:
        """Deterministic canonical SHA-256 fingerprint per AKAAL_CANONICAL_PROFILE_V1."""
        from akaalPipeline.contracts.serialization import canonical_fingerprint
        return canonical_fingerprint(dict(self.resolved_values))

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved_values": dict(self.resolved_values),
            "provenance": dict(self.provenance),
            "overrides": dict(self.overrides),
            "fingerprint": self.fingerprint,
        }

