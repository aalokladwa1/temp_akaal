"""
Akaal — Multi-Dimensional Complexity Model
===========================================
Composed migration complexity score evaluating structural, semantic, operational, performance, and scale complexity.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MigrationComplexity:
    structural_complexity: float = 0.0
    semantic_complexity: float = 0.0
    operational_complexity: float = 0.0
    performance_complexity: float = 0.0
    scale_complexity: float = 0.0
    overall_complexity_score: float = 0.0
    complexity_tier: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    complexity_drivers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structural_complexity": round(self.structural_complexity, 2),
            "semantic_complexity": round(self.semantic_complexity, 2),
            "operational_complexity": round(self.operational_complexity, 2),
            "performance_complexity": round(self.performance_complexity, 2),
            "scale_complexity": round(self.scale_complexity, 2),
            "overall_complexity_score": round(self.overall_complexity_score, 2),
            "complexity_tier": self.complexity_tier,
            "complexity_drivers": self.complexity_drivers,
        }
