"""
Akaal — Type Conversion Public Models
=====================================
Contains the public, immutable domain models and enums for type conversion.
"""

import re
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Set

class TypeCategory(str, Enum):
    NUMERIC = "NUMERIC"
    STRING = "STRING"
    DATE_TIME = "DATE_TIME"
    BOOLEAN = "BOOLEAN"
    BINARY = "BINARY"
    JSON = "JSON"
    UUID = "UUID"
    LOB = "LOB"
    CLOB = "CLOB"
    BLOB = "BLOB"


class ConversionStatus(str, Enum):
    LOSSLESS = "LOSSLESS"
    LOSSY = "LOSSY"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, order=True)
class DbVersion:
    """Represents a database semantic or custom version string and handles ordering."""
    major: int
    minor: int
    patch: int = 0
    raw: str = field(default="", compare=False)

    @classmethod
    def parse(cls, version_str: str) -> 'DbVersion':
        if not version_str:
            return cls(0, 0, 0, "")
        version_clean = version_str.strip().lower()
        # Matches e.g. "13.5", "8.0.25", "19c", "2016", "23ai"
        match = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?.*$', version_clean)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2)) if match.group(2) else 0
            patch = int(match.group(3)) if match.group(3) else 0
            return cls(major, minor, patch, version_str)
        
        # Fallback to leading numeric characters
        match_leading = re.match(r'^(\d+).*$', version_clean)
        if match_leading:
            return cls(int(match_leading.group(1)), 0, 0, version_str)
        return cls(0, 0, 0, version_str)


@dataclass(frozen=True)
class SpatialMetadata:
    crs_id: int
    dimension: int
    geometry_type: str  # e.g. "POINT", "POLYGON"


@dataclass(frozen=True)
class DataType:
    """Represents a database-specific data type with all associated attributes."""
    name: str
    category: TypeCategory
    precision: Optional[int] = None
    scale: Optional[int] = None
    length: Optional[int] = None
    nullable: bool = True
    unsigned: bool = False
    auto_increment: bool = False
    timezone: bool = False
    charset: Optional[str] = None
    collation: Optional[str] = None
    spatial: Optional[SpatialMetadata] = None
    is_array: bool = False
    array_dimensions: Optional[int] = None
    generated_expression: Optional[str] = None
    vendor_metadata: Dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        """Generates a deterministic SHA-256 fingerprint for caching/validation."""
        components = [
            self.name.upper(),
            self.category.value,
            str(self.precision),
            str(self.scale),
            str(self.length),
            str(self.nullable),
            str(self.unsigned),
            str(self.auto_increment),
            str(self.timezone),
            self.charset or "",
            self.collation or "",
            str(self.spatial.crs_id if self.spatial else ""),
            str(self.spatial.dimension if self.spatial else ""),
            str(self.spatial.geometry_type if self.spatial else ""),
            str(self.is_array),
            str(self.array_dimensions),
            self.generated_expression or ""
        ]
        serialized = ":".join(components).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()


@dataclass(frozen=True)
class ConversionPolicy:
    """Configures policies governing the rules matching and validation pipeline."""
    allow_precision_loss: bool = True
    allow_lossy_conversions: bool = True
    default_string_length: int = 255
    default_numeric_precision: int = 18
    default_numeric_scale: int = 2
    enforce_strict_nullability: bool = True
    policy_overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversionContext:
    """Immutable collection containing all relevant metadata for a conversion execution."""
    source_vendor: str
    source_version: DbVersion
    target_vendor: str
    target_version: DbVersion
    policy: ConversionPolicy
    schema_metadata: Dict[str, Any] = field(default_factory=dict)
    ai_hints: Dict[str, Any] = field(default_factory=dict)
    custom_overrides: Tuple[Any, ...] = field(default_factory=tuple)
    plugin_context: Dict[str, Any] = field(default_factory=dict)
