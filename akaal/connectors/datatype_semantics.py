"""
Akaal — Canonical Datatype Semantic Model & Type Capability Intersections (P4.8)
==============================================================================
Consolidated with AKAAL Canonical Schema Engine (akaal.schema.domain.types and type_registry).
Reuses CanonicalTypeCategory, CanonicalType, ConversionSafety, and CanonicalTypeRegistry as the SINGLE source of datatype truth.
"""

from typing import Dict, Any, Optional, List
from akaal.schema.domain.types import (
    CanonicalTypeCategory,
    CanonicalType,
    ConversionSafety,
)
from akaal.schema.domain.type_registry import CanonicalTypeRegistry

# Re-alias SemanticDatatypeFamily to CanonicalTypeCategory for backward compatibility
SemanticDatatypeFamily = CanonicalTypeCategory


class DatatypeDimensions:
    """Datatype dimensions wrapping CanonicalType fields without duplicating metadata."""

    def __init__(
        self,
        precision: Optional[int] = None,
        scale: Optional[int] = None,
        signed: bool = True,
        width_bytes: Optional[int] = None,
        max_length: Optional[int] = None,
        encoding: str = "UTF-8",
        collation: Optional[str] = None,
        timezone_aware: bool = False,
        nullable: bool = True,
        dimensionality: int = 0,
    ) -> None:
        self.precision = precision
        self.scale = scale
        self.signed = signed
        self.width_bytes = width_bytes
        self.max_length = max_length
        self.encoding = encoding
        self.collation = collation
        self.timezone_aware = timezone_aware
        self.nullable = nullable
        self.dimensionality = dimensionality

    def to_dict(self) -> Dict[str, Any]:
        return {
            "precision": self.precision,
            "scale": self.scale,
            "signed": self.signed,
            "width_bytes": self.width_bytes,
            "max_length": self.max_length,
            "encoding": self.encoding,
            "collation": self.collation,
            "timezone_aware": self.timezone_aware,
            "nullable": self.nullable,
            "dimensionality": self.dimensionality,
        }


def map_vendor_type_to_semantic_family(vendor_name: str, native_type_name: str) -> CanonicalTypeCategory:
    """Delegates O(1) type normalization to CanonicalTypeRegistry, returning CanonicalTypeCategory."""
    canon_type = CanonicalTypeRegistry.normalize_source_type(vendor_name, native_type_name)
    return canon_type.category
