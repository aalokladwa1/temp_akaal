"""
Akaal — Multi-Dimensional Cutover Readiness Model
=================================================
Composed readiness evaluating technical, operational, infrastructure, and data readiness.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ReadinessClassification(str, Enum):
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    HIGH_RISK = "HIGH_RISK"
    NOT_READY = "NOT_READY"


@dataclass
class CutoverReadiness:
    technical_readiness: float = 100.0
    operational_readiness: float = 100.0
    infrastructure_readiness: float = 100.0
    data_readiness: float = 100.0
    classification: ReadinessClassification = ReadinessClassification.READY
    blockers: List[str] = field(default_factory=list)
    required_manual_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "technical_readiness": round(self.technical_readiness, 2),
            "operational_readiness": round(self.operational_readiness, 2),
            "infrastructure_readiness": round(self.infrastructure_readiness, 2),
            "data_readiness": round(self.data_readiness, 2),
            "classification": self.classification.value if hasattr(self.classification, "value") else str(self.classification),
            "blockers": self.blockers,
            "required_manual_steps": self.required_manual_steps,
        }
