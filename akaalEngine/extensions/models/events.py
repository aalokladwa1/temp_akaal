"""
akaalEngine.extensions.models.events
====================================
Internal typed event models for extension registration, activation, deactivation, and lifecycle updates.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional

from akaalEngine.extensions.models.identity import ExtensionId, ProviderId, RegistryGeneration, StrategyId


class ExtensionEventType(str, Enum):
    """Event types emitted during extension operations."""
    EXTENSION_REGISTERED = "EXTENSION_REGISTERED"
    EXTENSION_ACTIVATED = "EXTENSION_ACTIVATED"
    EXTENSION_DEACTIVATED = "EXTENSION_DEACTIVATED"
    EXTENSION_UNAVAILABLE = "EXTENSION_UNAVAILABLE"
    EXTENSION_FAULTED = "EXTENSION_FAULTED"
    EXTENSION_REPLACED = "EXTENSION_REPLACED"
    EXTENSION_REMOVED = "EXTENSION_REMOVED"
    REGISTRY_GENERATION_CHANGED = "REGISTRY_GENERATION_CHANGED"
    DEPENDENCY_STATE_CHANGED = "DEPENDENCY_STATE_CHANGED"
    PROVIDER_CONTRIBUTION_CHANGED = "PROVIDER_CONTRIBUTION_CHANGED"


@dataclass(frozen=True)
class ExtensionEvent:
    """Immutable event payload delivered to internal engine listeners."""
    event_type: ExtensionEventType
    extension_id: ExtensionId
    generation: RegistryGeneration
    provider_id: Optional[ProviderId] = None
    strategy_id: Optional[StrategyId] = None
    timestamp: float = field(default_factory=time.time)
    details: Mapping[str, Any] = field(default_factory=dict)
