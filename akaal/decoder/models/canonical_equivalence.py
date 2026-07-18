"""
Akaal — Semantic Mapping & Equivalence Model
===========================================
Rich semantic mapping classification model replacing simple compatibility matrix percentages.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class SemanticEquivalenceType(str, Enum):
    EQUIVALENT = "EQUIVALENT"
    SUBTYPE = "SUBTYPE"
    SUPERTYPE = "SUPERTYPE"
    LOSSLESS = "LOSSLESS"
    LOSSY = "LOSSY"
    PARTIAL = "PARTIAL"
    REQUIRES_TRANSFORMATION = "REQUIRES_TRANSFORMATION"
    EMULATED = "EMULATED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class SemanticEquivalence:
    """Semantic Equivalence metadata model."""
    equivalence_type: SemanticEquivalenceType
    confidence_score: float = 100.0  # 0 to 100
    is_lossless: bool = True
    reason: str = "Direct semantic mapping"
    warnings: List[str] = field(default_factory=list)
    fallback_strategy: str = "NONE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "equivalence_type": self.equivalence_type.value if hasattr(self.equivalence_type, "value") else str(self.equivalence_type),
            "confidence_score": self.confidence_score,
            "is_lossless": self.is_lossless,
            "reason": self.reason,
            "warnings": self.warnings,
            "fallback_strategy": self.fallback_strategy,
        }
