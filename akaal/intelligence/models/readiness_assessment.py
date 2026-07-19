"""
AKAAL Enterprise Intelligence Platform — Readiness Assessment Model
====================================================================
Represents multi-dimensional enterprise cutover readiness scoring (0.0 to 100.0).
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Tuple
from akaal.intelligence.models.enterprise_intelligence_enums import ReadinessTier


@dataclass(frozen=True)
class ReadinessAssessment:
    """
    Immutable representation of enterprise cutover readiness assessment.
    """

    assessment_id: str
    overall_readiness_score: float  # 0.0 to 100.0
    tier: ReadinessTier
    schema_readiness_score: float  # 0.0 to 100.0
    data_readiness_score: float    # 0.0 to 100.0
    hardware_readiness_score: float # 0.0 to 100.0
    operational_readiness_score: float # 0.0 to 100.0
    critical_blockers: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    remediation_steps: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.critical_blockers, tuple):
            object.__setattr__(self, "critical_blockers", tuple(self.critical_blockers))
        if not isinstance(self.warnings, tuple):
            object.__setattr__(self, "warnings", tuple(self.warnings))
        if not isinstance(self.remediation_steps, tuple):
            object.__setattr__(self, "remediation_steps", tuple(self.remediation_steps))

        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self,
                "metadata",
                MappingProxyType(dict(self.metadata) if self.metadata else {}),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts object to Python dictionary."""
        return {
            "assessment_id": self.assessment_id,
            "overall_readiness_score": float(self.overall_readiness_score),
            "tier": self.tier.value if hasattr(self.tier, "value") else str(self.tier),
            "schema_readiness_score": float(self.schema_readiness_score),
            "data_readiness_score": float(self.data_readiness_score),
            "hardware_readiness_score": float(self.hardware_readiness_score),
            "operational_readiness_score": float(self.operational_readiness_score),
            "critical_blockers": list(self.critical_blockers),
            "warnings": list(self.warnings),
            "remediation_steps": list(self.remediation_steps),
            "metadata": dict(self.metadata),
        }
