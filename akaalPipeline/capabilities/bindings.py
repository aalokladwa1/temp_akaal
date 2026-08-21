"""akaalPipeline.capabilities.bindings
======================================
Engine binding descriptors & registry for physical engine ports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Set
from akaalPipeline.contracts.enums import MigrationMode


@dataclass(frozen=True)
class EngineBindingDescriptor:
    binding_id: str
    engine_name: str
    version: str
    port_instance: Any  # Port implementation object satisfying engine port protocols
    is_healthy: bool = True
    supported_capabilities: Set[str] = field(default_factory=set)
    supported_modes: Set[MigrationMode] = field(default_factory=set)
    contract_version: str = "1.0.0"




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
