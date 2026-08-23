"""
akaalEngine.schema.assessment.risk
==================================
Evidence-based structural semantic risk scoring engine.
Evaluates deterministic risk points across unsupported types, lossiness, LOBs, UDTs, and circular dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, List, Mapping, Optional, Tuple

from akaalEngine.schema.assessment.compatibility import CompatibilityBreakdown
from akaalEngine.schema.models.schema import CanonicalSchemaModel


class RiskLevel(str, Enum):
    """Evidence-based migration risk tiers."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class RiskFactor:
    """A specific evidence-backed risk contributor."""
    category: str
    description: str
    impact_score: int
    affected_object: Optional[str] = None


@dataclass(frozen=True)
class StructuralRiskReport:
    """Consolidated structural risk score and evidence report."""
    total_risk_score: int
    risk_level: RiskLevel
    risk_factors: Tuple[RiskFactor, ...] = field(default_factory=tuple)
    extra: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.risk_factors, tuple):
            object.__setattr__(self, "risk_factors", tuple(self.risk_factors))
        if not isinstance(self.extra, MappingProxyType):
            object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_risk_score": self.total_risk_score,
            "risk_level": self.risk_level.value,
            "risk_factors": [
                {
                    "category": f.category,
                    "description": f.description,
                    "impact_score": f.impact_score,
                    "affected_object": f.affected_object,
                }
                for f in self.risk_factors
            ],
            "extra": dict(self.extra),
        }


class StructuralRiskScorer:
    """Computes deterministic risk score and assigns risk tiers based on concrete evidence."""

    @classmethod
    def score_risk(
        cls,
        model: CanonicalSchemaModel,
        compat_breakdown: CompatibilityBreakdown,
    ) -> StructuralRiskReport:
        factors: List[RiskFactor] = []
        score = 0

        # 1. Unsupported Datatypes (+50 per unsupported type)
        if compat_breakdown.unsupported_count > 0:
            impact = compat_breakdown.unsupported_count * 50
            score += impact
            factors.append(
                RiskFactor(
                    category="UNSUPPORTED_TYPES",
                    description=f"{compat_breakdown.unsupported_count} column(s) contain datatypes unsupported by target engine",
                    impact_score=impact,
                )
            )

        # 2. Lossy Datatypes (+20 per lossy conversion)
        if compat_breakdown.lossy_count > 0:
            impact = compat_breakdown.lossy_count * 20
            score += impact
            factors.append(
                RiskFactor(
                    category="LOSSY_CONVERSIONS",
                    description=f"{compat_breakdown.lossy_count} column(s) will undergo lossy precision/length conversion",
                    impact_score=impact,
                )
            )

        # 3. LOBs (+10 per LOB column)
        lob_cols = 0
        for tbl in model.tables:
            for col in tbl.columns:
                if col.is_lob:
                    lob_cols += 1
        if lob_cols > 0:
            impact = lob_cols * 10
            score += impact
            factors.append(
                RiskFactor(
                    category="LOB_COMPLEXITY",
                    description=f"{lob_cols} LOB/BLOB/CLOB column(s) require large-payload streaming migration",
                    impact_score=impact,
                )
            )

        # 4. User-Defined Types (+15 per UDT)
        if len(model.udts) > 0:
            impact = len(model.udts) * 15
            score += impact
            factors.append(
                RiskFactor(
                    category="UDT_COMPLEXITY",
                    description=f"{len(model.udts)} user-defined type(s) require custom mapping or conversion",
                    impact_score=impact,
                )
            )

        # 5. Determine Risk Level
        if score > 120:
            level = RiskLevel.CRITICAL
        elif score > 60:
            level = RiskLevel.HIGH
        elif score > 20:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        return StructuralRiskReport(
            total_risk_score=score,
            risk_level=level,
            risk_factors=tuple(factors),
        )
