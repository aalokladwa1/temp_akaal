"""
akaalEngine.schema.assessment.compatibility
===========================================
Pre-migration schema compatibility assessment across all objects and data types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple

from akaalEngine.schema.assessment.lossiness import LossinessAssessment, LossinessEngine
from akaalEngine.schema.models.schema import CanonicalSchemaModel
from akaalEngine.schema.models.types import ConversionSafety, freeze_deep
from akaalEngine.schema.types.registry import CanonicalTypeRegistry


@dataclass(frozen=True)
class CompatibilityBreakdown:
    """Statistical breakdown of datatype conversion safety across the entire schema."""
    total_columns: int
    exact_count: int
    equivalent_count: int
    transformed_count: int
    compat_layer_count: int
    lossy_count: int
    unsupported_count: int
    decision_required_count: int
    lossy_assessments: Tuple[LossinessAssessment, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.lossy_assessments, tuple):
            object.__setattr__(self, "lossy_assessments", tuple(self.lossy_assessments))
        object.__setattr__(self, "extra", freeze_deep(self.extra))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_columns": self.total_columns,
            "exact_count": self.exact_count,
            "equivalent_count": self.equivalent_count,
            "transformed_count": self.transformed_count,
            "compat_layer_count": self.compat_layer_count,
            "lossy_count": self.lossy_count,
            "unsupported_count": self.unsupported_count,
            "decision_required_count": self.decision_required_count,
            "lossy_assessments": [a.to_dict() for a in self.lossy_assessments],
            "extra": dict(self.extra),
        }

    @property
    def is_compatible(self) -> bool:
        """True if there are zero unsupported, lossy, or decision-required column types."""
        return self.unsupported_count == 0 and self.lossy_count == 0 and self.decision_required_count == 0


class PreMigrationCompatibilityAssessor:
    """Assesses whole-schema compatibility against a target database engine."""

    @classmethod
    def assess_model(
        cls,
        model: CanonicalSchemaModel,
        target_engine: str,
    ) -> CompatibilityBreakdown:
        total_cols = 0
        exact = 0
        equiv = 0
        trans = 0
        compat = 0
        lossy = 0
        unsupp = 0
        decision = 0
        lossy_assessments: List[LossinessAssessment] = []

        for tbl in model.tables:
            for col in tbl.columns:
                total_cols += 1
                emission = CanonicalTypeRegistry.emit_target_type(target_engine, col.canonical_type)

                if emission.safety == ConversionSafety.EXACT:
                    exact += 1
                elif emission.safety == ConversionSafety.SEMANTICALLY_EQUIVALENT:
                    equiv += 1
                elif emission.safety == ConversionSafety.COMPATIBLE_WITH_TRANSFORMATION:
                    trans += 1
                elif emission.safety == ConversionSafety.COMPATIBILITY_LAYER_REQUIRED:
                    compat += 1
                elif emission.safety == ConversionSafety.LOSSY:
                    lossy += 1
                    assessment = LossinessEngine.assess_column(f"{tbl.qualified_name}.{col.name}", col.canonical_type, emission)
                    lossy_assessments.append(assessment)
                elif emission.safety == ConversionSafety.UNSUPPORTED:
                    unsupp += 1
                    assessment = LossinessEngine.assess_column(f"{tbl.qualified_name}.{col.name}", col.canonical_type, emission)
                    lossy_assessments.append(assessment)
        # Evaluate dropped foreign keys from mapping exclusions
        dropped_fks = model.extra.get("dropped_foreign_keys", ())
        extra_meta = dict(model.extra)
        if dropped_fks:
            decision += len(dropped_fks)
            extra_meta["dropped_foreign_keys_count"] = len(dropped_fks)

        return CompatibilityBreakdown(
            total_columns=total_cols,
            exact_count=exact,
            equivalent_count=equiv,
            transformed_count=trans,
            compat_layer_count=compat,
            lossy_count=lossy,
            unsupported_count=unsupp,
            decision_required_count=decision,
            lossy_assessments=tuple(lossy_assessments),
            extra=extra_meta,
        )
