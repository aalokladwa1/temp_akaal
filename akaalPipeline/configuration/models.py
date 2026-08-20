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
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    PROJECT = "project"
    MIGRATION = "migration"
    PLAN = "plan"
    INITIALIZATION = "initialization"


@dataclass(frozen=True)
class ConfigurationLayer:
    scope: ConfigurationScope
    settings: Mapping[str, Any]


@dataclass(frozen=True)
class EffectiveConfiguration:
    resolved_values: Mapping[str, Any]
    provenance: Mapping[str, str]  # key -> scope string
    overrides: Mapping[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.resolved_values.get(key, default)
