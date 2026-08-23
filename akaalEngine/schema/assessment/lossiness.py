"""
akaalEngine.schema.assessment.lossiness
=======================================
17 Standardized machine-readable lossiness reason codes and lossiness evaluation engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, List, Mapping, Optional, Tuple

from akaalEngine.schema.models.types import CanonicalType, ConversionSafety, TargetTypeEmission


class LossinessReasonCode(str, Enum):
    """The 17 standardized machine-readable lossiness reason codes."""
    TARGET_PRECISION_INSUFFICIENT = "TARGET_PRECISION_INSUFFICIENT"
    SCALE_REDUCTION_LOSSY = "SCALE_REDUCTION_LOSSY"
    STRING_TRUNCATION_RISK = "STRING_TRUNCATION_RISK"
    TIMEZONE_SEMANTICS_LOSSY = "TIMEZONE_SEMANTICS_LOSSY"
    BINARY_LENGTH_LIMITATION = "BINARY_LENGTH_LIMITATION"
    UNSUPPORTED_TYPE_CONVERSION = "UNSUPPORTED_TYPE_CONVERSION"
    FLOATING_POINT_IMPRECISION = "FLOATING_POINT_IMPRECISION"
    UNSIGNED_TO_SIGNED_OVERFLOW = "UNSIGNED_TO_SIGNED_OVERFLOW"
    BIT_WIDTH_NARROWING = "BIT_WIDTH_NARROWING"
    JSON_DOCUMENT_FALLBACK = "JSON_DOCUMENT_FALLBACK"
    ARRAY_ELEMENT_LOSS = "ARRAY_ELEMENT_LOSS"
    SPATIAL_SRID_UNSUPPORTED = "SPATIAL_SRID_UNSUPPORTED"
    VECTOR_DIMENSION_MISMATCH = "VECTOR_DIMENSION_MISMATCH"
    UDT_STRUCTURE_FLATTENED = "UDT_STRUCTURE_FLATTENED"
    LOB_STORAGE_DEGRADED = "LOB_STORAGE_DEGRADED"
    COLLATION_NORMALIZED = "COLLATION_NORMALIZED"
    NULLABILITY_RELAXED = "NULLABILITY_RELAXED"


@dataclass(frozen=True)
class LossinessAssessment:
    """Assessment of potential data or precision loss for a specific column or datatype conversion."""
    column_name: str
    source_type: str
    target_type: str
    safety: ConversionSafety
    reasons: Tuple[LossinessReasonCode, ...] = field(default_factory=tuple)
    description: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.reasons, tuple):
            object.__setattr__(self, "reasons", tuple(self.reasons))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "column_name": self.column_name,
            "source_type": self.source_type,
            "target_type": self.target_type,
            "safety": self.safety.value,
            "reasons": [r.value for r in self.reasons],
            "description": self.description,
            "extra": dict(self.extra),
        }


class LossinessEngine:
    """Evaluates column lossiness and maps to the 17 standardized reason codes."""

    @classmethod
    def assess_column(
        cls,
        column_name: str,
        canonical_type: CanonicalType,
        target_emission: TargetTypeEmission,
    ) -> LossinessAssessment:
        reasons: List[LossinessReasonCode] = []
        for r_str in target_emission.lossiness_reasons:
            try:
                reasons.append(LossinessReasonCode(r_str))
            except ValueError:
                pass

        return LossinessAssessment(
            column_name=column_name,
            source_type=canonical_type.raw_vendor_type,
            target_type=target_emission.target_native_type,
            safety=target_emission.safety,
            reasons=tuple(reasons),
            description=target_emission.warning_message,
        )
