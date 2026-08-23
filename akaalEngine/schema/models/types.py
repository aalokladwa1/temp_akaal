"""
akaalEngine.schema.models.types
===============================
Canonical datatype categories, representations, conversion safety classifications,
and target emission containers for Authority #4 Schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional


class CanonicalTypeCategory(str, Enum):
    """Universal 14-category canonical datatype classification."""
    EXACT_NUMERIC = "EXACT_NUMERIC"
    APPROX_NUMERIC = "APPROX_NUMERIC"
    CHARACTER = "CHARACTER"
    BINARY = "BINARY"
    DATETIME = "DATETIME"
    INTERVAL = "INTERVAL"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"
    XML = "XML"
    SPATIAL = "SPATIAL"
    VECTOR = "VECTOR"
    UDT = "UDT"
    LOB = "LOB"
    ARRAY = "ARRAY"
    UNKNOWN = "UNKNOWN"


class ConversionSafety(str, Enum):
    """7-state type conversion safety and lossiness classification."""
    EXACT = "EXACT"
    SEMANTICALLY_EQUIVALENT = "SEMANTICALLY_EQUIVALENT"
    COMPATIBLE_WITH_TRANSFORMATION = "COMPATIBLE_WITH_TRANSFORMATION"
    COMPATIBILITY_LAYER_REQUIRED = "COMPATIBILITY_LAYER_REQUIRED"
    LOSSY = "LOSSY"
    UNSUPPORTED = "UNSUPPORTED"
    USER_DECISION_REQUIRED = "USER_DECISION_REQUIRED"


def freeze_deep(val: Any) -> Any:
    """Recursively converts dictionaries to MappingProxyType, sets to deterministically sorted tuples, and sequences to immutable tuples."""
    if isinstance(val, (dict, MappingProxyType)):
        return MappingProxyType({k: freeze_deep(v) for k, v in val.items()})
    elif isinstance(val, (set, frozenset)):
        try:
            sorted_items = sorted(val)
        except TypeError:
            sorted_items = sorted(val, key=lambda x: str(x))
        return tuple(freeze_deep(item) for item in sorted_items)
    elif isinstance(val, list):
        return tuple(freeze_deep(item) for item in val)
    elif isinstance(val, tuple):
        return tuple(freeze_deep(item) for item in val)
    return val


@dataclass(frozen=True)
class CanonicalType:
    """
    Immutable canonical type intermediate representation (IR).
    Represents semantic type dimensions independently of specific database vendor dialects.
    """
    category: CanonicalTypeCategory
    raw_vendor_type: str
    precision: Optional[int] = None
    scale: Optional[int] = None
    length: Optional[int] = None
    byte_semantics: bool = False
    is_signed: bool = True
    bits: Optional[int] = None
    is_timezone_aware: bool = False
    timezone_offset_preserved: bool = False
    array_element_type: Optional[CanonicalType] = None
    element_type_name: Optional[str] = None
    dimensions: Optional[int] = None  # Vector/array dimensions
    srid: Optional[int] = None        # Spatial SRID
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "raw_vendor_type": self.raw_vendor_type,
            "precision": self.precision,
            "scale": self.scale,
            "length": self.length,
            "byte_semantics": self.byte_semantics,
            "is_signed": self.is_signed,
            "bits": self.bits,
            "is_timezone_aware": self.is_timezone_aware,
            "timezone_offset_preserved": self.timezone_offset_preserved,
            "array_element_type": self.array_element_type.to_dict() if self.array_element_type else None,
            "element_type_name": self.element_type_name,
            "dimensions": self.dimensions,
            "srid": self.srid,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CanonicalType:
        arr_elem = None
        if data.get("array_element_type"):
            arr_elem = cls.from_dict(data["array_element_type"])
        return cls(
            category=CanonicalTypeCategory(data.get("category", "UNKNOWN")),
            raw_vendor_type=data.get("raw_vendor_type", "UNKNOWN"),
            precision=data.get("precision"),
            scale=data.get("scale"),
            length=data.get("length"),
            byte_semantics=data.get("byte_semantics", False),
            is_signed=data.get("is_signed", True),
            bits=data.get("bits"),
            is_timezone_aware=data.get("is_timezone_aware", False),
            timezone_offset_preserved=data.get("timezone_offset_preserved", False),
            array_element_type=arr_elem,
            element_type_name=data.get("element_type_name"),
            dimensions=data.get("dimensions"),
            srid=data.get("srid"),
            extra=data.get("extra", {}),
        )


@dataclass(frozen=True)
class TargetTypeEmission:
    """Target-native DDL type emission container with safety classification and warnings."""
    target_engine: str
    target_native_type: str
    safety: ConversionSafety = ConversionSafety.EXACT
    warning_message: Optional[str] = None
    lossiness_reasons: tuple[str, ...] = field(default_factory=tuple)
    requires_runtime_cast: bool = False
    requires_compat_helper: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.lossiness_reasons, tuple):
            object.__setattr__(self, "lossiness_reasons", tuple(self.lossiness_reasons))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_engine": self.target_engine,
            "target_native_type": self.target_native_type,
            "safety": self.safety.value,
            "warning_message": self.warning_message,
            "lossiness_reasons": list(self.lossiness_reasons),
            "requires_runtime_cast": self.requires_runtime_cast,
            "requires_compat_helper": self.requires_compat_helper,
            "extra": dict(self.extra),
        }
