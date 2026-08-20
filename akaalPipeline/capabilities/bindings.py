"""akaalPipeline.capabilities.bindings
======================================
Engine binding descriptors & registry for physical engine ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(frozen=True)
class EngineBindingDescriptor:
    binding_id: str
    engine_name: str
    version: str
    is_healthy: bool
    port_instance: Any  # Port implementation object satisfying engine port protocols


class BindingRegistry:
    def __init__(self) -> None:
        self._bindings: dict[str, EngineBindingDescriptor] = {}

    def register(self, descriptor: EngineBindingDescriptor) -> None:
        self._bindings[descriptor.binding_id] = descriptor

    def unregister(self, binding_id: str) -> None:
        self._bindings.pop(binding_id, None)

    def get(self, binding_id: str) -> Optional[EngineBindingDescriptor]:
        return self._bindings.get(binding_id)

    def list_all(self) -> List[EngineBindingDescriptor]:
        return list(self._bindings.values())
