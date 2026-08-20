"""akaalPipeline.extensions.descriptors
======================================
Extension & plugin descriptors.
Registration does NOT make a capability AVAILABLE without valid engine binding & capability resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ExtensionDescriptor:
    extension_id: str
    name: str
    version: str
    capability_contracts: List[str] = field(default_factory=list)
    author: Optional[str] = None


class ExtensionRegistry:
    def __init__(self) -> None:
        self._extensions: dict[str, ExtensionDescriptor] = {}

    def register(self, extension: ExtensionDescriptor) -> None:
        self._extensions[extension.extension_id] = extension

    def unregister(self, extension_id: str) -> None:
        self._extensions.pop(extension_id, None)

    def get(self, extension_id: str) -> Optional[ExtensionDescriptor]:
        return self._extensions.get(extension_id)

    def list_all(self) -> List[ExtensionDescriptor]:
        return list(self._extensions.values())
