"""
Akaal — Canonical Type Algebra
==============================
Canonical Type System featuring 16 top-level type families, extensible parameters, and OpaqueType fallback.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CanonicalTypeFamily(str, Enum):
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"
    INTERVAL = "INTERVAL"
    UUID = "UUID"
    BINARY = "BINARY"
    UNICODE_STRING = "UNICODE_STRING"
    JSON = "JSON"
    XML = "XML"
    ARRAY = "ARRAY"
    SPATIAL = "SPATIAL"
    IDENTITY = "IDENTITY"
    SEQUENCE_REFERENCE = "SEQUENCE_REFERENCE"
    LARGE_OBJECT = "LARGE_OBJECT"
    OPAQUE = "OPAQUE"


@dataclass
class CanonicalType:
    """Canonical Type Algebra model."""
    family: CanonicalTypeFamily
    name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)  # precision, scale, length, etc.
    attributes: Dict[str, Any] = field(default_factory=dict)  # nullable, unsigned, etc.
    extensions: Dict[str, Any] = field(default_factory=dict)
    vendor_metadata: Dict[str, Any] = field(default_factory=dict)
    semantic_metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["CanonicalType"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family.value if hasattr(self.family, "value") else str(self.family),
            "name": self.name or self.family.value,
            "parameters": self.parameters,
            "attributes": self.attributes,
            "extensions": self.extensions,
            "vendor_metadata": self.vendor_metadata,
            "semantic_metadata": self.semantic_metadata,
            "children": [c.to_dict() for c in self.children],
        }


def OpaqueType(raw_vendor_type: str, vendor_engine: str = "UNKNOWN") -> CanonicalType:
    """Fallback representation for unknown or custom vendor data types."""
    return CanonicalType(
        family=CanonicalTypeFamily.OPAQUE,
        name=f"OPAQUE[{raw_vendor_type}]",
        vendor_metadata={"raw_type": raw_vendor_type, "vendor_engine": vendor_engine},
        semantic_metadata={"is_opaque": True, "requires_custom_handler": True},
    )
