"""
AKAAL Schema Engine — Universal Canonical Datatype Model
=========================================================
Defines the database-agnostic canonical datatype representation and conversion safety
classifications used across Oracle, PostgreSQL, MySQL, MSSQL, and future connectors.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List


class CanonicalTypeCategory(str, Enum):
    """Semantic datatype families in the AKAAL Canonical Type System."""
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    FIXED_DECIMAL = "DECIMAL"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    CHAR = "CHAR"
    VARCHAR = "VARCHAR"
    VARIABLE_STRING = "VARCHAR"
    TEXT = "TEXT"
    LARGE_TEXT = "TEXT"
    BINARY = "BINARY"
    VARBINARY = "VARBINARY"
    BLOB = "BLOB"
    LARGE_BINARY = "BLOB"
    DATE = "DATE"
    TIME = "TIME"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMPTZ = "TIMESTAMPTZ"
    TIMESTAMP_WITH_TIMEZONE = "TIMESTAMPTZ"
    UUID = "UUID"
    JSON = "JSON"
    JSONB = "JSONB"
    XML = "XML"
    INTERVAL = "INTERVAL"
    ENUM = "ENUM"
    ARRAY = "ARRAY"
    GEOMETRY = "GEOMETRY"
    VECTOR = "VECTOR"
    DOCUMENT = "DOCUMENT"
    VARIANT = "VARIANT"
    UNKNOWN = "UNKNOWN"
    UNKNOWN_VENDOR_TYPE = "UNKNOWN"


class ConversionSafety(str, Enum):
    """Risk/Safety classification for type conversions across database engines."""
    EXACT = "EXACT"
    SAFE = "SAFE"
    POTENTIALLY_LOSSY = "POTENTIALLY_LOSSY"
    LOSSY = "LOSSY"
    UNSUPPORTED = "UNSUPPORTED"
    VENDOR_SPECIFIC = "VENDOR_SPECIFIC"


@dataclass
class CanonicalType:
    """Database-agnostic representation of a column's semantic data type."""
    category: CanonicalTypeCategory
    raw_vendor_type: str
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    bits: Optional[int] = None  # 8, 16, 32, 64, 128
    is_signed: bool = True
    is_unicode: bool = False
    timezone_aware: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_canonical_string(self) -> str:
        """Return a readable canonical summary string."""
        attrs = []
        if self.bits:
            attrs.append(f"bits={self.bits}")
        if self.length:
            attrs.append(f"len={self.length}")
        if self.precision is not None:
            attrs.append(f"prec={self.precision}")
        if self.scale is not None:
            attrs.append(f"scale={self.scale}")
        if self.is_unicode:
            attrs.append("unicode=True")
        if self.timezone_aware:
            attrs.append("tz=True")
        if not self.is_signed:
            attrs.append("unsigned=True")
        attr_str = f"({', '.join(attrs)})" if attrs else ""
        return f"Canonical{self.category.value.title()}{attr_str}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "raw_vendor_type": self.raw_vendor_type,
            "length": self.length,
            "precision": self.precision,
            "scale": self.scale,
            "bits": self.bits,
            "is_signed": self.is_signed,
            "is_unicode": self.is_unicode,
            "timezone_aware": self.timezone_aware,
            "canonical_string": self.to_canonical_string(),
            "extra": self.extra,
        }


@dataclass
class TargetTypeEmission:
    """Result of emitting a target-native SQL datatype from a CanonicalType."""
    target_engine: str
    target_native_type: str
    safety: ConversionSafety
    warning_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_engine": self.target_engine,
            "target_native_type": self.target_native_type,
            "safety": self.safety.value,
            "warning_message": self.warning_message,
        }
