"""akaalPipeline.capabilities.catalog
======================================
Capability catalog defining static metadata descriptors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Mapping, Set
from akaalPipeline.contracts.enums import MigrationMode, SideEffectClassification


@dataclass(frozen=True)
class CapabilityDescriptor:
    capability_id: str
    name: str
    supported_modes: Set[MigrationMode]
    side_effect: SideEffectClassification
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)


class CapabilityCatalog:
    def __init__(self) -> None:
        self._catalog: dict[str, CapabilityDescriptor] = {}

    def register(self, descriptor: CapabilityDescriptor) -> None:
        self._catalog[descriptor.capability_id] = descriptor

    def get(self, capability_id: str) -> CapabilityDescriptor | None:
        return self._catalog.get(capability_id)

    def list_all(self) -> List[CapabilityDescriptor]:
        return list(self._catalog.values())
