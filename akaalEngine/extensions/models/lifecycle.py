"""
akaalEngine.extensions.models.lifecycle
=======================================
Models representing extension lifecycle state transitions and audit records.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from akaalEngine.extensions.models.enums import ExtensionLifecycleState
from akaalEngine.extensions.models.identity import ExtensionId, RegistryGeneration


@dataclass(frozen=True)
class TransitionRecord:
    """Immutable audit record of a state transition."""
    extension_id: ExtensionId
    from_state: ExtensionLifecycleState
    to_state: ExtensionLifecycleState
    generation: RegistryGeneration
    reason: str
    timestamp: float = field(default_factory=time.time)
    operator: Optional[str] = None


@dataclass(frozen=True)
class ExtensionLifecycleSnapshot:
    """Current lifecycle state of an extension."""
    extension_id: ExtensionId
    current_state: ExtensionLifecycleState
    generation: RegistryGeneration
    active_handle_count: int
    last_transition_at: float
    last_transition_reason: str
