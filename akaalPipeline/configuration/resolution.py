"""akaalPipeline.configuration.resolution
=========================================
Configuration precedence resolution & presentation filtering.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Mapping
from akaalPipeline.configuration.models import ConfigurationLayer, ConfigurationScope, EffectiveConfiguration


class PresentationIntent(str, Enum):
    STANDARD = "STANDARD"
    ADVANCED = "ADVANCED"


# Precedence order: Platform -> Org -> Workspace -> Project -> Migration -> Plan -> Initialization
PRECEDENCE_ORDER = [
    ConfigurationScope.PLATFORM,
    ConfigurationScope.ORGANIZATION,
    ConfigurationScope.WORKSPACE,
    ConfigurationScope.PROJECT,
    ConfigurationScope.MIGRATION,
    ConfigurationScope.PLAN,
    ConfigurationScope.INITIALIZATION,
]


class ConfigurationResolver:
    @staticmethod
    def resolve(layers: List[ConfigurationLayer]) -> EffectiveConfiguration:
        resolved: dict[str, Any] = {}
        provenance: dict[str, str] = {}
        overrides: dict[str, Any] = {}

        # Sort layers by precedence order
        layer_map = {layer.scope: layer for layer in layers}
        for scope in PRECEDENCE_ORDER:
            if scope in layer_map:
                layer = layer_map[scope]
                for k, v in layer.settings.items():
                    if k in resolved:
                        overrides[k] = v
                    resolved[k] = v
                    provenance[k] = scope.value

        return EffectiveConfiguration(
            resolved_values=resolved,
            provenance=provenance,
            overrides=overrides,
        )

    @staticmethod
    def filter_presentation(
        effective_config: EffectiveConfiguration,
        intent: PresentationIntent = PresentationIntent.STANDARD,
    ) -> Mapping[str, Any]:
        """Filters presentation intent without altering single underlying runtime resolution."""
        if intent == PresentationIntent.ADVANCED:
            return effective_config.resolved_values

        # Standard intent exposes only non-internal, standard parameters
        return {k: v for k, v in effective_config.resolved_values.items() if not k.startswith("_") and not k.startswith("advanced_")}
