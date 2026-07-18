"""
Akaal — Canonical Capability Model
==================================
Hierarchical capability profile model representing normalized platform capabilities.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CapabilityProfileNode:
    name: str
    supported: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    sub_capabilities: List["CapabilityProfileNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "supported": self.supported,
            "parameters": self.parameters,
            "sub_capabilities": [c.to_dict() for c in self.sub_capabilities],
        }


@dataclass
class CanonicalCapabilityModel:
    """Canonical platform capability model."""
    capabilities: Dict[str, CapabilityProfileNode] = field(default_factory=dict)

    def set_capability(self, name: str, supported: bool = True, parameters: Optional[Dict[str, Any]] = None) -> None:
        self.capabilities[name] = CapabilityProfileNode(
            name=name,
            supported=supported,
            parameters=parameters or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self.capabilities.items()}
